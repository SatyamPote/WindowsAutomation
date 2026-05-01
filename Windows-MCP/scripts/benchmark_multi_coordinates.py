from __future__ import annotations

import argparse
import statistics
from time import perf_counter

from windows_mcp.desktop.service import Desktop
from windows_mcp.desktop.views import DesktopState
from windows_mcp.tree.views import (
    BoundingBox,
    Center,
    ScrollElementNode,
    TreeElementNode,
    TreeState,
)


def build_desktop(interactive_count: int, scrollable_count: int) -> Desktop:
    desktop = Desktop.__new__(Desktop)
    interactive_nodes = [
        TreeElementNode(
            bounding_box=BoundingBox(
                left=i,
                top=i,
                right=i + 10,
                bottom=i + 10,
                width=10,
                height=10,
            ),
            center=Center(x=i + 5, y=i + 5),
            name=f"Button {i}",
            control_type="Button",
            window_name="Notepad",
        )
        for i in range(interactive_count)
    ]
    scrollable_nodes = [
        ScrollElementNode(
            name=f"Scrollable {i}",
            control_type="Pane",
            window_name="Notepad",
            bounding_box=BoundingBox(
                left=i,
                top=i,
                right=i + 12,
                bottom=i + 12,
                width=12,
                height=12,
            ),
            center=Center(x=i + 6, y=i + 6),
        )
        for i in range(scrollable_count)
    ]
    desktop.desktop_state = DesktopState(
        active_desktop={"name": "Desktop 1"},
        all_desktops=[],
        active_window=None,
        windows=[],
        tree_state=TreeState(
            interactive_nodes=interactive_nodes,
            scrollable_nodes=scrollable_nodes,
        ),
    )
    return desktop


def build_labels(interactive_count: int, scrollable_count: int, repeats: int) -> list[int]:
    label_pool = list(range(interactive_count + scrollable_count))
    return label_pool * repeats


def iterative_resolution(desktop: Desktop, labels: list[int]) -> list[tuple[int, int]]:
    return [desktop.get_coordinates_from_label(label) for label in labels]


def bulk_resolution(desktop: Desktop, labels: list[int]) -> list[tuple[int, int]]:
    return desktop.get_coordinates_from_labels(labels)


def measure(fn, desktop: Desktop, labels: list[int], runs: int) -> list[float]:
    timings: list[float] = []
    for _ in range(runs):
        start = perf_counter()
        fn(desktop, labels)
        timings.append(perf_counter() - start)
    return timings


def summarize(name: str, timings: list[float]) -> tuple[float, float, float]:
    avg = statistics.mean(timings)
    minimum = min(timings)
    maximum = max(timings)
    print(f"{name}_avg={avg:.6f}s")
    print(f"{name}_min={minimum:.6f}s")
    print(f"{name}_max={maximum:.6f}s")
    return avg, minimum, maximum


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark iterative versus bulk coordinate resolution for multi-label desktop tools.",
    )
    parser.add_argument("--interactive-count", type=int, default=500)
    parser.add_argument("--scrollable-count", type=int, default=200)
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args()

    desktop = build_desktop(args.interactive_count, args.scrollable_count)
    labels = build_labels(args.interactive_count, args.scrollable_count, args.repeats)

    # Warm up both paths.
    iterative_resolution(desktop, labels)
    bulk_resolution(desktop, labels)

    iterative_timings = measure(iterative_resolution, desktop, labels, args.runs)
    bulk_timings = measure(bulk_resolution, desktop, labels, args.runs)

    iterative_avg, _, _ = summarize("iterative", iterative_timings)
    bulk_avg, _, _ = summarize("bulk", bulk_timings)

    improvement = ((iterative_avg - bulk_avg) / iterative_avg * 100) if iterative_avg else 0.0
    print(f"improvement={improvement:.2f}%")
    print(f"labels_per_run={len(labels)}")
    print(f"interactive_nodes={args.interactive_count}")
    print(f"scrollable_nodes={args.scrollable_count}")
    print(f"runs={args.runs}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
