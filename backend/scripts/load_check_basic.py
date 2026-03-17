import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Endpoint:
    name: str
    method: str
    path: str


ENDPOINTS: list[Endpoint] = [
    Endpoint("overview", "GET", "/api/v1/me"),
    Endpoint("candidates:list", "GET", "/api/v1/candidates?limit=20"),
    Endpoint("leads:list", "GET", "/api/v1/leads?limit=20"),
    Endpoint("companies:list", "GET", "/api/v1/companies?limit=20"),
    Endpoint("invoices:list", "GET", "/api/v1/invoices?limit=20"),
]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * p
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return values_sorted[f]
    d0 = values_sorted[f] * (c - k)
    d1 = values_sorted[c] * (k - f)
    return d0 + d1


async def login(client: httpx.AsyncClient, base_url: str, email: str, password: str) -> str:
    r = await client.post(f"{base_url}/api/v1/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


async def hit(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    tenant_id: str,
    ep: Endpoint,
) -> tuple[int, float]:
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id}
    t0 = time.perf_counter()
    r = await client.request(ep.method, f"{base_url}{ep.path}", headers=headers)
    dt = (time.perf_counter() - t0) * 1000.0
    return r.status_code, dt


async def run() -> None:
    base_url = os.environ.get("HF_BASE_URL", "http://127.0.0.1:8000")
    email = os.environ.get("HF_EMAIL", "admin@hostflow.dev")
    password = os.environ.get("HF_PASSWORD", "admin")
    tenant_id = os.environ.get("HF_TENANT_ID", "11111111-1111-1111-1111-111111111111")
    concurrency = int(os.environ.get("HF_CONCURRENCY", "10"))
    iterations = int(os.environ.get("HF_ITERATIONS", "200"))

    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        token = await login(client, base_url, email, password)

        results: dict[str, dict[str, object]] = {}
        for ep in ENDPOINTS:
            latencies: list[float] = []
            errors = 0

            sem = asyncio.Semaphore(concurrency)

            async def one() -> None:
                nonlocal errors
                async with sem:
                    try:
                        status, ms = await hit(client, base_url, token, tenant_id, ep)
                        latencies.append(ms)
                        if status >= 500 or status == 0:
                            errors += 1
                    except Exception:
                        errors += 1

            await asyncio.gather(*[one() for _ in range(iterations)])

            results[ep.name] = {
                "iterations": iterations,
                "concurrency": concurrency,
                "errors": errors,
                "p50_ms": percentile(latencies, 0.50),
                "p95_ms": percentile(latencies, 0.95),
                "p99_ms": percentile(latencies, 0.99),
                "avg_ms": (statistics.fmean(latencies) if latencies else 0.0),
                "min_ms": (min(latencies) if latencies else 0.0),
                "max_ms": (max(latencies) if latencies else 0.0),
            }

        payload = {
            "ts": int(time.time()),
            "base_url": base_url,
            "tenant_id": tenant_id,
            "endpoints": results,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(run())

