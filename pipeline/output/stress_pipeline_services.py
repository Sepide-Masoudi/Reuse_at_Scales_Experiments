import requests
import threading
import time
from time import perf_counter

DURATION = 300  # 5 minutes
TIMEOUT = 30

# ---------- SERVICE CALLS ----------

def call_generate_name():
    return requests.post(
        "http://generate-name-knative.pipeline.svc.cluster.local/run",
        files={
            "n_rows": (None, "1000"),
            "mf_ratio": (None, "0.5"),
            "output_path": (None, "/mnt/data/argo-shard/test/names.csv"),
        },
        timeout=TIMEOUT,
    )

def call_generate_birthday():
    return requests.post(
        "http://generate-birthday-knative.pipeline.svc.cluster.local/run",
        files={
            "n_rows": (None, "1000"),
            "min_age": (None, "18"),
            "max_age": (None, "80"),
            "output_file": (None, "/mnt/data/argo-shard/test/birthdays.csv"),
        },
        timeout=TIMEOUT,
    )

def call_generate_address():
    return requests.post(
        "http://generate-address-knative.pipeline.svc.cluster.local/run",
        files={
            "n_rows": (None, "1000"),
            "output_file": (None, "/mnt/data/argo-shard/test/addresses.csv"),
        },
        timeout=TIMEOUT,
    )

def call_generate_id():
    return requests.post(
        "http://generate-id-knative.pipeline.svc.cluster.local/run",
        files={
            "name_csv": (None, "/mnt/data/argo-shard/test/names.csv"),
            "birthday_csv": (None, "/mnt/data/argo-shard/test/birthdays.csv"),
            "output_file": (None, "/mnt/data/argo-shard/test/id.csv"),
        },
        timeout=TIMEOUT,
    )

def call_preprocess():
    return requests.post(
        "http://data-preprocess-knative.pipeline.svc.cluster.local/run",
        files={
            "metadata_file": (None, "/mnt/data/argo-shard/test/meta.json"),
            "input_file": (None, "/mnt/data/argo-shard/test/id.csv"),
            "output_file": (None, "/mnt/data/argo-shard/test/clean.csv"),
            "handle_missing": (None, "mean"),
        },
        timeout=TIMEOUT,
    )

def call_synth():
    return requests.post(
        "http://synthetic-generator-knative.pipeline.svc.cluster.local/run",
        files={
            "metadata_json": (None, "/mnt/data/argo-shard/test/meta.json"),
            "input_csv": (None, "clean.csv"),
            "input_dir": (None, "/mnt/data/argo-shard/test"),
            "output_file": (None, "/mnt/data/argo-shard/test/synth.csv"),
            "n_rows": (None, "1000"),
            "method": (None, "realistic"),
        },
        timeout=TIMEOUT,
    )

def call_quality():
    return requests.post(
        "http://data-quality-knative.pipeline.svc.cluster.local/run",
        files={
            "input_metadata_file": (None, "/mnt/data/argo-shard/test/meta.json"),
            "input_file_real": (None, "/mnt/data/argo-shard/test/clean.csv"),
            "input_file_synth": (None, "/mnt/data/argo-shard/test/synth.csv"),
            "output_dir": (None, "/mnt/data/argo-shard/test/quality"),
            "metrics": (None, "realistic"),
        },
        timeout=TIMEOUT,
    )

def call_privacy():
    return requests.post(
        "http://privacy-tracking-knative.pipeline.svc.cluster.local/run",
        files={
            "input_dir": (None, "/mnt/data/argo-shard/test"),
            "real_csv": (None, "clean.csv"),
            "synth_csv": (None, "synth.csv"),
            "output_file": (None, "/mnt/data/argo-shard/test/privacy.json"),
        },
        timeout=TIMEOUT,
    )

PIPELINE_CALLS = [
    call_generate_name,
    call_generate_birthday,
    call_generate_address,
    call_generate_id,
    call_preprocess,
    call_synth,
    call_quality,
    call_privacy,
]

# ---------- EXECUTION ----------

def run_pipeline_once(stats):
    for fn in PIPELINE_CALLS:
        start = perf_counter()
        try:
            r = fn()
            stats.append((r.status_code, perf_counter() - start))
        except Exception:
            stats.append(("ERR", 0))


def wave(users, stats):
    barrier = threading.Barrier(users)

    def worker():
        barrier.wait()
        run_pipeline_once(stats)

    threads = [threading.Thread(target=worker) for _ in range(users)]
    for t in threads: t.start()
    for t in threads: t.join()


def run_level(users):
    print(f"\n=== {users} concurrent users for 5 minutes ===")
    end = time.time() + DURATION
    stats = []

    if users == 0:
        while time.time() < end:
            run_pipeline_once(stats)
    else:
        while time.time() < end:
            wave(users, stats)

    ok = [s for s in stats if s[0] == 200]
    print("Total calls:", len(stats))
    print("Success:", len(ok))


if __name__ == "__main__":
    for level in [0, 5, 50]:
        run_level(level)
