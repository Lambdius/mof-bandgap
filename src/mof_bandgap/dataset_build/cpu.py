import logging
import os

logger = logging.getLogger(__name__)


def available_cpu_count() -> int:
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            quota, period = f.read().split()
        if quota != "max":
            n = max(1, int(quota) // int(period))
            logger.info("[Dataset] cgroup v2 cpu.max reports %d usable core(s)", n)
            return n
    except (FileNotFoundError, ValueError):
        pass

    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as f:
            quota_us = int(f.read())
        with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as f:
            period_us = int(f.read())
        if quota_us > 0:
            n = max(1, quota_us // period_us)
            logger.info("[Dataset] cgroup v1 cfs_quota reports %d usable core(s)", n)
            return n
    except (FileNotFoundError, ValueError):
        pass

    try:
        n = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
        logger.info("[Dataset] os.sched_getaffinity reports %d usable core(s)", n)
        return n
    except AttributeError:
        pass

    n = os.cpu_count() or 1
    logger.info("[Dataset] no cgroup limit found, falling back to os.cpu_count(): %d core(s)", n)
    return n
