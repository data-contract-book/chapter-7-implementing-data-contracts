#!/usr/bin/env python3
"""
met_scraper.py

Bulk-download records from The Met Collection API.  Two modes of operation:

1. *Search mode* (`--search-first`):  
   • Performs the highlight + hasImages search endpoint once.  
   • Saves the raw search response to a JSON file.  
   • Uses the returned `objectIDs` to fetch every object record.

2. *ID-file mode* (`--ids-file`):  
   • Reads a JSON list of object IDs you supply.  
   • Fetches each corresponding object record.

All fetched objects are appended to a single JSON array (`objects.json`
by default).  A checkpoint log (`processed_ids.log`) allows the script to
resume safely after interruption.  The request rate never exceeds
80 requests/minute (1.0s delay between calls).

DATA SOURCE:
    The Metropolitan Museum of Art Collection API
    https://metmuseum.github.io/
    https://github.com/metmuseum/openaccess
    Data under CC0-1.0 license
        https://github.com/metmuseum/openaccess?tab=CC0-1.0-1-ov-file#readme

Execute Script:
python get_data_subset_from_met_api.py \
  --search-first \
  --out objects.json \
  --checkpoint processed_ids.log
"""

import argparse
import json
import logging
import os
import pathlib
import time
from typing import List, Set, Tuple

import requests


class MetScraper:
    """Download Met object records with optional pre-search and restart-safety."""

    OBJECT_URL = (
        "https://collectionapi.metmuseum.org/public/collection/v1/objects/{}"
    )
    SEARCH_URL = (
        "https://collectionapi.metmuseum.org/public/collection/v1/"
        "search?isHighlight=true&hasImages=true&q=*"
        )

    def __init__(
        self,
        ids_file: str | None = None,
        out_file: str = "objects.json",
        checkpoint_file: str = "processed_ids.log",
        search_first: bool = False,
        search_out_file: str = "search_results.json",
        rate_delay_sec: float = 1.00,
        flush_every: int = 25,
    ):
        """
        Parameters
        ----------
        ids_file : str | None
            JSON file containing a list of object IDs.  Ignored if
            `search_first` is True.
        out_file : str
            Destination file for the combined JSON array of objects.
        checkpoint_file : str
            Log file storing one completed ID per line for restart safety.
        search_first : bool
            If True, run the highlight + hasImages search and use its IDs.
        search_out_file : str
            Where to save the raw search JSON (only used when search_first).
        rate_delay_sec : float
            Seconds to wait between individual object fetches.
        flush_every : int
            Flush file handles after this many successful writes.
        """
        # Paths
        self.ids_path = pathlib.Path(ids_file) if ids_file else None
        self.out_path = pathlib.Path(out_file)
        self.checkpoint_path = pathlib.Path(checkpoint_file)
        self.search_out_path = pathlib.Path(search_out_file)

        # Settings
        self.search_first = search_first
        self.rate_delay_sec = rate_delay_sec
        self.flush_every = flush_every

        # Networking
        self.session = requests.Session()

        # ID lists
        if self.search_first:
            self.all_ids = self._perform_search()
        else:
            if not self.ids_path:
                raise ValueError("Provide --ids-file or use --search-first.")
            self.all_ids = self._load_ids(self.ids_path)

        self.done_ids = self._load_checkpoint()
        self.pending = [object_id for object_id in self.all_ids if object_id not in self.done_ids]
        self.bad_ids: List[int] = []

    def _load_ids(self, path: pathlib.Path) -> List[int]:
        """Return a list of IDs from *path*, which must be a JSON array."""
        with path.open("r", encoding="utf-8") as f:
            return list(map(int, json.load(f)))

    def _load_checkpoint(self) -> Set[int]:
        """Load completed IDs from the checkpoint file (may be empty)."""
        if not self.checkpoint_path.exists():
            return set()
        with self.checkpoint_path.open("r", encoding="utf-8") as f:
            return {int(line.strip()) for line in f if line.strip()}

    def _perform_search(self) -> List[int]:
        """
        Execute the Met object search, save raw JSON,
        and return the list of object IDs.
        """
        logging.info(f"Fetching object IDs from search: {self.SEARCH_URL}…")
        resp = self.session.get(self.SEARCH_URL, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        with self.search_out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"Saved search response to {self.search_out_path}")

        ids = data.get("objectIDs") or []
        id_len = len(ids)
        logging.info(f"Search returned {id_len} IDs")
        return list(map(int, ids))

    def _prepare_output(self) -> Tuple[object, bool]:
        """
        Open the JSON array file for appending.

        Returns
        -------
        handle : io.TextIOBase
            File handle open for append.
        first_item_flag : bool
            True if the array is empty and the next write will be the first
            element (no leading comma needed).
        """
        if not self.out_path.exists() or self.out_path.stat().st_size == 0:
            handle = self.out_path.open("w", encoding="utf-8")
            handle.write("[\n")
            return handle, True

        # Strip closing bracket and any trailing comma/whitespace.
        with self.out_path.open("rb+") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            # Trim whitespace
            while end > 0:
                end -= 1
                f.seek(end)
                if f.read(1) not in b" \t\r\n":
                    break
            f.seek(end)
            last = f.read(1)
            if last == b"]":
                f.truncate(end)
                # Trim again to check for trailing comma
                while end > 0:
                    end -= 1
                    f.seek(end)
                    if f.read(1) not in b" \t\r\n":
                        break
                f.seek(end)
                last = f.read(1)
            if last == b",":
                f.truncate(end)

        handle = self.out_path.open("a", encoding="utf-8")
        return handle, False

    def _finalize_output(self, handle) -> None:
        """Write the closing bracket for the JSON array and close *handle*."""
        handle.write("\n]\n")
        handle.close()

    def _append_json(self, handle, obj: dict, first_item: bool) -> None:
        """
        Append *obj* to the open JSON array file.

        A leading comma is written unless *first_item* is True.
        """
        if not first_item:
            handle.write(",\n")
        json.dump(obj, handle, ensure_ascii=False)

    def _process_id(self, object_id: int, handle, first_item_flag: bool) -> bool:
        """
        Fetch a single object ID.

        Backoff logic:
            - start with 5-second wait if were throttled
            - cap the sleep at 2 minutes
            - 1 initial try + up to {max_attempts} retries
        Returns
        -------
        success : bool
            True if the object was fetched and written; False after all attempts fail.
        """
        backoff = 5
        max_backoff = 120
        max_attempts = 4

        for attempt in range(max_attempts):
            try:
                resp = self.session.get(self.OBJECT_URL.format(object_id), timeout=20)

                if resp.status_code == 200:
                    self._append_json(handle, resp.json(), first_item_flag)
                    with self.checkpoint_path.open("a", encoding="utf-8") as log:
                        log.write(f"{object_id}\n")
                    return True

                if resp.status_code in (403, 429):
                    logging.warning(
                        f"ID {object_id} → HTTP {resp.status_code} "
                        f"(attempt {attempt + 1}/{max_attempts}) – backing off {backoff} s"
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                    continue

                # --- OTHER NON-200, treat as hard failure ---------------------
                logging.warning(f"ID {object_id} → HTTP {resp.status_code} (no retry)")
                break

            except requests.RequestException as exc:
                logging.warning(
                    f"ID {object_id} → {exc} "
                    f"(attempt {attempt + 1}/{max_attempts}) – backing off {backoff} s"
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

        # After all retries
        self.bad_ids.append(object_id)
        return False

    def run(self) -> None:
        """Download every pending object and write it to the output JSON."""
        logging.info(
            f"Total IDs: {len(self.all_ids)} | "
            f"Completed: {len(self.done_ids)} | "
            f"Remaining: {len(self.pending)}"
            )

        handle, first_item = self._prepare_output()
        start = time.perf_counter()

        try:
            for i, object_id in enumerate(self.pending, 1):
                success = self._process_id(object_id, handle, first_item)
                if success and first_item:
                    first_item = False

                if i % self.flush_every == 0:
                    handle.flush()
                    logging.info(
                        "Progress: %d / %d (%.1f%%)",
                        i,
                        len(self.pending),
                        100 * i / len(self.pending),
                    )
                time.sleep(self.rate_delay_sec)
        finally:
            self._finalize_output(handle)

        mins = (time.perf_counter() - start) / 60
        logging.info(
            "Done in %.1f min | Success: %d | Failed: %d",
            mins,
            len(self.pending) - len(self.bad_ids),
            len(self.bad_ids),
        )
        if self.bad_ids:
            with open("failed_ids.json", "w", encoding="utf-8") as f:
                json.dump(self.bad_ids, f, indent=2)
            logging.info("Wrote failed IDs to failed_ids.json")

def _parse_args(argv=None):
    """Return parsed command-line arguments."""
    p = argparse.ArgumentParser(
        description="Download Met object records with restart safety."
    )
    p.add_argument("--ids-file", help="JSON list of object IDs to fetch")
    p.add_argument(
        "--search-first",
        action="store_true",
        help="Run highlight+hasImages search and use its IDs",
    )
    p.add_argument(
        "--search-out",
        default="search_results.json",
        help="Destination for raw search JSON (search-first only)",
    )
    p.add_argument("--out", default="objects.json", help="Output JSON array")
    p.add_argument(
        "--checkpoint",
        default="processed_ids.log",
        help="Checkpoint log file (one ID per line)",
    )
    p.add_argument(
        "--rate-delay",
        default=1.00,
        type=float,
        help="Seconds to wait between object requests",
    )
    p.add_argument(
        "--flush-every",
        default=25,
        type=int,
        help="Flush files to disk after this many writes",
    )
    return p.parse_args(argv)


def main() -> None:
    """Parse CLI flags, build a scraper, and run it."""
    args = _parse_args()
    scraper = MetScraper(
        ids_file=args.ids_file,
        out_file=args.out,
        checkpoint_file=args.checkpoint,
        search_first=args.search_first,
        search_out_file=args.search_out,
        rate_delay_sec=args.rate_delay,
        flush_every=args.flush_every,
    )
    scraper.run()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.INFO,
    )
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Interrupted by user — safe to rerun later.")