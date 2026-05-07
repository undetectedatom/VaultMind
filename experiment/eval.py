import json
import time
import requests
import pandas as pd
from tqdm import tqdm

CONFIG_PATH = "experiment_config.json"

# Pricing Table (Per 1,000 tokens)
COST_TABLE = {
    "doubao-seed-2.0-pro": {"prompt": 0.0008, "completion": 0.002},
    "deepseek-v3.2": {"prompt": 0.0001, "completion": 0.0002},
}


class ExperimentRunner:
    def __init__(self):
        with open(CONFIG_PATH, "r") as f:
            self.config = json.load(f)
        self.base_url = self.config["api_base_url"]
        self.cluster_tokens = {}

    def authenticate_users(self):
        """Logs in all users and stores their active tokens in memory."""
        print("🔐 Authenticating Test Users...")
        for cluster, c_data in self.config["clusters"].items():
            res = requests.post(
                f"{self.base_url}/auth/token",
                data={"username": c_data["username"], "password": c_data["password"]},
            )
            res.raise_for_status()
            self.cluster_tokens[cluster] = res.json()["access_token"]
        print("✅ All users authenticated.\n")

    def evaluate_recall_and_mrr(self, retrieved_sources, expected_filename):
        if not expected_filename or not retrieved_sources:
            return 0.0, 0.0
        filenames = [src.get("filename", "") for src in retrieved_sources]
        recall = 1.0 if expected_filename in filenames else 0.0
        try:
            mrr = 1.0 / (filenames.index(expected_filename) + 1)
        except ValueError:
            mrr = 0.0
        return recall, mrr

    def calculate_exact_cost(self, model_name, prompt_tokens, comp_tokens):
        rates = COST_TABLE.get(
            model_name, {"prompt": 0.001, "completion": 0.002}
        )  # Fallback
        return (prompt_tokens / 1000.0) * rates["prompt"] + (
            comp_tokens / 1000.0
        ) * rates["completion"]

    def run(self):
        self.authenticate_users()

        with open(self.config["dataset_path"], "r", encoding="utf-8") as f:
            dataset = json.load(f)

        results = []
        print("Starting Evaluation...\n")

        for item in tqdm(dataset, desc="Processing Queries"):
            cluster = item["cluster"]
            token = self.cluster_tokens.get(cluster)
            headers = {"Authorization": f"Bearer {token}"}

            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.base_url}/v1/chat",
                    headers=headers,
                    json={"query": item["query"]},
                    timeout=145,
                )
                response.raise_for_status()
                res_data = response.json()
            except Exception as e:
                print(f"\n API Error on {item['id']}: {e}")
                continue

            latency = time.time() - start_time
            sources = res_data.get("sources", [])
            meta = res_data.get("meta") or res_data.get("metadata", {})

            # 1. Retrieval Metrics
            recall, mrr = self.evaluate_recall_and_mrr(
                sources, item["expected_doc_filename"]
            )

            # 2. Rejection Metric
            rejection_acc = 0.0
            if item["is_out_of_bounds"]:
                rejection_acc = 1.0 if len(sources) == 0 else 0.0

            # 3. Exact Cost Metrics
            selected_model = meta.get("selected_model", "unknown")
            p_tokens = meta.get("prompt_tokens", 0)
            c_tokens = meta.get("completion_tokens", 0)
            exact_cost = self.calculate_exact_cost(selected_model, p_tokens, c_tokens)

            results.append(
                {
                    "id": item["id"],
                    "cluster": cluster,
                    "question_type": item["question_type"],
                    "latency_sec": round(latency, 2),
                    "exact_cost": exact_cost,
                    "recall_at_4": recall,
                    "mrr": mrr,
                    "rejection_acc": rejection_acc,
                    "llm_complexity": meta.get("llm_complexity_score", 0),
                    "retrieval_confidence": meta.get("retrieval_confidence", 0),
                    "selected_model": selected_model,
                    "used_hyde": "hyde_document" in meta,
                    "prompt_tokens": p_tokens,
                    "completion_tokens": c_tokens,
                }
            )
            time.sleep(1)

        # Export Results
        df = pd.DataFrame(results)
        df.to_csv(self.config["output_csv_path"], index=False)
        print(f"\n✅ Results saved to {self.config['output_csv_path']}")


if __name__ == "__main__":
    runner = ExperimentRunner()
    runner.run()
