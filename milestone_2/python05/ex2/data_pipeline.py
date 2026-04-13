#!/usr/bin/env python3

import sys
import os
from typing import Any, Protocol, runtime_checkable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ex0'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ex1'))

from data_processor import (  # noqa: E402
    NumericProcessor, TextProcessor, LogProcessor
)
from data_stream import DataStream  # noqa: E402


@runtime_checkable
class ExportPlugin(Protocol):
    def process_output(self, data: list[tuple[int, str]]) -> None:
        ...


class CSVExportPlugin:
    def process_output(self, data: list[tuple[int, str]]) -> None:
        if not data:
            return
        values = ",".join(item for _, item in data)
        print("CSV Output:")
        print(values)


class JSONExportPlugin:
    def process_output(self, data: list[tuple[int, str]]) -> None:
        if not data:
            return
        obj = {f"item_{rank}": value for rank, value in data}
        print("JSON Output:")
        print("{" + ", ".join(f'"{k}": "{v}"' for k, v in obj.items()) + "}")


class DataStreamWithPipeline(DataStream):

    def output_pipeline(self, nb: int, plugin: ExportPlugin) -> None:
        for proc in self._processors:
            collected: list[tuple[int, str]] = []
            for _ in range(nb):
                try:
                    collected.append(proc.output())
                except IndexError:
                    break
            if collected:
                plugin.process_output(collected)


if __name__ == "__main__":
    print("=== Code Nexus - Data Pipeline ===")
    print()
    print("Initialize Data Stream...")

    ds = DataStreamWithPipeline()
    ds.print_processors_stats()

    print()
    print("Registering Processors")
    ds.register_processor(NumericProcessor())
    ds.register_processor(TextProcessor())
    ds.register_processor(LogProcessor())

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
    print()
    ds.print_processors_stats()

    print()
    print("Send 3 processed data from each processor to a CSV plugin:")
    csv_plugin = CSVExportPlugin()
    ds.output_pipeline(3, csv_plugin)
    print()
    ds.print_processors_stats()

    batch2: list[Any] = [
        21,
        ["I love AI", "LLMs are wonderful", "Stay healthy"],
        [{"log_level": "ERROR", "log_message": "500 server crash"},
         {"log_level": "NOTICE", "log_message": "Certificate expires in 10 days"}],
        [32, 42, 64, 84, 128, 168],
        "World hello",
    ]
    print()
    print(f"Send another batch of data: {batch2}")
    ds.process_stream(batch2)
    print()
    ds.print_processors_stats()

    print()
    print("Send 5 processed data from each processor to a JSON plugin:")
    json_plugin = JSONExportPlugin()
    ds.output_pipeline(5, json_plugin)
    print()
    ds.print_processors_stats()
