#!/usr/bin/env python3

import sys
import os
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ex0'))

from data_processor import (  # noqa: E402
    DataProcessor, NumericProcessor, TextProcessor, LogProcessor
)


class DataStream:

    def __init__(self) -> None:
        self._processors: list[DataProcessor] = []

    def register_processor(self, proc: DataProcessor) -> None:
        self._processors.append(proc)

    def process_stream(self, stream: list[Any]) -> None:
        for element in stream:
            handled = False
            for proc in self._processors:
                if proc.validate(element):
                    proc.ingest(element)
                    handled = True
                    break
            if not handled:
                print(f"DataStream error - Can't process element "
                      f"in stream: {element}")

    def print_processors_stats(self) -> None:
        print("== DataStream statistics ==")
        if not self._processors:
            print("No processor found, no data")
            return
        for proc in self._processors:
            name = type(proc).__name__
            remaining = len(proc._storage)
            total = proc._rank + remaining
            print(f"{name}: total {total} items processed, "
                  f"remaining {remaining} on processor")


if __name__ == "__main__":
    print("=== Code Nexus - Data Stream ===")
    print()
    print("Initialize Data Stream...")

    ds = DataStream()
    ds.print_processors_stats()

    print()
    print("Registering Numeric Processor")
    ds.register_processor(NumericProcessor())

    batch1: list[Any] = [
        "Hello world",
        [3.14, -1, 2.71],
        [{"log_level": "WARNING",
          "log_message": "Telnet access! Use ssh instead"},
         {"log_level": "INFO",
          "log_message": "User wil is connected"}],
        42,
        ["Hi", "five"],
    ]
    print(f"Send first batch of data on stream: {batch1}")
    ds.process_stream(batch1)
    print("== DataStream statistics ==")
    ds.print_processors_stats()

    print()
    print("Registering other data processors")
    ds.register_processor(TextProcessor())
    ds.register_processor(LogProcessor())
    print("Send the same batch again")
    ds.process_stream(batch1)
    ds.print_processors_stats()

    print()
    print("Consume some elements from the data processors: Numeric 3, Text 2, Log 1")
    numeric_proc = ds._processors[0]
    text_proc = ds._processors[1]
    log_proc = ds._processors[2]
    for _ in range(3):
        numeric_proc.output()
    for _ in range(2):
        text_proc.output()
    for _ in range(1):
        log_proc.output()
    ds.print_processors_stats()
