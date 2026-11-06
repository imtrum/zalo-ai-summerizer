import logging
from datetime import datetime

from zalo_ai.config.logging_config import setup_logging
from zalo_ai.targets.json_store import get_enabled_targets
from zalo_ai.config.timezone import VN_TZ
from zalo_ai.workflows import run_summarization


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        cutoff_text = input(
            "Enter cutoff (YYYY-MM-DD HH:MM, Vietnam time): "
        ).strip()
        cutoff = datetime.strptime(
            cutoff_text,
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=VN_TZ)

        summaries = run_summarization(
            cutoff,
            on_status=logger.info,
        )
        target_names = {
            target["id"]: target["name"]
            for target in get_enabled_targets()
        }

        for target_id, summary in summaries.items():
            target_name = target_names.get(target_id, target_id)
            print(f"\n=== Summary for {target_name} ===")
            print(summary)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Cannot process input: %s", exc)
        raise
    except Exception:
        logger.exception("Unexpected error during summarization.")
        raise


if __name__ == "__main__":
    main()
