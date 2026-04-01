#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Any, List


class DataProcessor(ABC):
    @abstractmethod
    def process(self, data: Any) -> str:
        pass

    @abstractmethod
    def validate(self, data: Any) -> bool:
        pass

    def format_output(self, result: str) -> str:
        return f"Output: {result}"


class NumericProcessor(DataProcessor):
    def validate(self, data: Any) -> bool:
        if not isinstance(data, list):
            return False
        return all(isinstance(x, (int, float)) for x in data)

    def process(self, data: Any) -> str:
        if not self.validate(data):
            raise ValueError("Invalid numeric data")
        total = sum(data)
        avg = total / len(data)
        return f"Processed {len(data)} numeric values, sum={total}, avg={avg}"


class TextProcessor(DataProcessor):
    def validate(self, data: Any) -> bool:
        return isinstance(data, str)

    def process(self, data: Any) -> str:
        if not self.validate(data):
            raise ValueError("Invalid text data")
        chars = len(data)
        words = len(data.split())
        return f"Processed text: {chars} characters, {words} words"


class LogProcessor(DataProcessor):
    def validate(self, data: Any) -> bool:
        return isinstance(data, str)

    def process(self, data: Any) -> str:
        if not self.validate(data):
            raise ValueError("Invalid log data")
        if data.startswith("ERROR: "):
            return f"[ALERT] ERROR level detected: {data[7:]}"
        if data.startswith("INFO: "):
            return f"[INFO] INFO level detected: {data[6:]}"
        return f"[LOG] {data}"


if __name__ == "__main__":
    print("=== CODE NEXUS - DATA PROCESSOR FOUNDATION ===\n")

    numeric = NumericProcessor()
    print("Initializing Numeric Processor...")
    data1: List[Any] = [1, 2, 3, 4, 5]
    print(f"Processing data: {data1}")
    print("Validation: Numeric data verified")
    print(numeric.format_output(numeric.process(data1)))
    print()

    text = TextProcessor()
    print("Initializing Text Processor...")
    data2 = "Hello Nexus World"
    print(f'Processing data: "{data2}"')
    print("Validation: Text data verified")
    print(text.format_output(text.process(data2)))
    print()

    log = LogProcessor()
    print("Initializing Log Processor...")
    data3 = "ERROR: Connection timeout"
    print(f'Processing data: "{data3}"')
    print("Validation: Log entry verified")
    print(log.format_output(log.process(data3)))
    print()

    print("=== Polymorphic Processing Demo ===")
    print("Processing multiple data types through same interface...")

    processors: List[DataProcessor] = [
        NumericProcessor(),
        TextProcessor(),
        LogProcessor(),
    ]
    datasets: List[Any] = [[1, 2, 3], "Hello World", "INFO: System ready"]

    for i, (proc, data) in enumerate(zip(processors, datasets), 1):
        print(f"Result {i}: {proc.process(data)}")

    print("Foundation systems online. Nexus ready for advanced streams.")
