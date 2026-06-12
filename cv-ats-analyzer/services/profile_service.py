import json

from services.storage import DATA_DIR

PROFILE_PATH = DATA_DIR / "ats_profile.json"


def load_profile_config() -> tuple[dict, dict, list[str]]:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return (
        payload["ats_profile"],
        payload["template_catalog"],
        payload["popular_job_domains"],
    )


ATS_PROFILE, TEMPLATE_CATALOG, POPULAR_JOB_DOMAINS = load_profile_config()
