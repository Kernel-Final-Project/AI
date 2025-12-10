from __future__ import annotations

import logging

from worker.common.mq import consume

logger = logging.getLogger(__name__)


def run_product_worker() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger.info("product_worker 스켈레톤입니다. 구현 후 MQ consume 로직을 추가하세요.")
    # 추후 구현 시:
    # consume(queue_name, callback, mq_url)


if __name__ == "__main__":
    run_product_worker()
