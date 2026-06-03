/*
  Example 06 — run via the FastAPI sidecar's RPC API (Node + fetch).

  This drives the SAME rules.json through the sidecar that the Python and CLI
  variants use. The sidecar is asynchronous: `harmonize` returns a job_id, and
  you poll `get_job` until the job completes.

  Sidecar contract (verified against the framework):
    - All four file paths MUST be absolute.
    - output_file_path must not already exist unless overwrite=true.
    - replay_log_file_path is required; the sidecar writes a per-row replay log.
    - The output keeps every input column plus the targets (same shape as the
      Python API's expected_output.csv).

  Start the sidecar first (from the framework repo), then run this:

    API_PORT=8000 API_HOST=127.0.0.1 \
      harmonization-framework/venv/bin/harmonization-sidecar

    node 01-hello-harmonization/client.ts
*/

import * as path from "node:path";
import { fileURLToPath } from "node:url";
import {
  GetJobResponse,
  HarmonizeRequest,
  HarmonizeResponse,
  JOB_STATUS,
} from "../_shared/rpc_types.ts";
import { RpcClient } from "../_shared/rpc_client.ts";

const API_URL = process.env.API_URL ?? "http://localhost:8000/api";
const HARMONIZE_TIMEOUT_MS = 20_000;
const GET_JOB_TIMEOUT_MS = 5_000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const exampleDir = path.dirname(fileURLToPath(import.meta.url));
const abs = (...parts: string[]) => path.resolve(exampleDir, ...parts);

async function main() {
  const client = new RpcClient(API_URL);

  const params: HarmonizeRequest = {
    data_file_path: abs("input.csv"),
    rules_file_path: abs("rules.json"),
    replay_log_file_path: abs("replay.log"),
    output_file_path: abs("output_rpc.csv"),
    overwrite: true,
  };

  const start = await client.call<HarmonizeResponse>({
    method: "harmonize",
    params,
    timeoutMs: HARMONIZE_TIMEOUT_MS,
  });

  const jobId = start.job_id;
  console.log(`Harmonization started. job_id=${jobId}`);

  while (true) {
    const status = await client.call<GetJobResponse>({
      method: "get_job",
      params: { job_id: jobId },
      timeoutMs: GET_JOB_TIMEOUT_MS,
    });

    const job = status.result;
    console.log(`Progress: ${Math.round(job.progress * 100)}%`);

    if (job.status === JOB_STATUS.COMPLETED) {
      console.log(`Completed. Output: ${job.output_path}`);
      console.log(`Replay log: ${job.replay_log_path}`);
      break;
    }
    if (job.status === JOB_STATUS.FAILED) {
      console.error("Harmonization failed:", job.error ?? "unknown error");
      process.exit(1);
    }
    await sleep(300);
  }
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
