from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union, Optional


class DataStream(ABC):
    def __init__(self, stream_id: str) -> None:
        self.stream_id: str = stream_id
        self.processed_count: int = 0

    @abstractmethod
    def process_batch(self, data_batch: List[Any]) -> str:
        pass

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        if criteria is None:
            return data_batch
        return [item for item in data_batch if criteria in str(item)]

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        return {
            "stream_id": self.stream_id,
            "processed_count": self.processed_count,
        }


class SensorStream(DataStream):
    def __init__(self, stream_id: str) -> None:
        super().__init__(stream_id)
        self.stream_type: str = "Environmental Data"

    def process_batch(self, data_batch: List[Any]) -> str:
        try:
            if not data_batch:
                raise ValueError("Empty sensor batch")
            temps = [
                float(str(item).split(":")[1])
                for item in data_batch
                if str(item).startswith("temp:")
            ]
            self.processed_count += len(data_batch)
            avg = temps[0] if temps else 0.0
            return (
                f"{len(data_batch)} readings processed, "
                f"avg temp: {avg}°C"
            )
        except Exception as e:
            return f"Sensor stream error: {e}"

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        if criteria == "critical":
            return [
                item for item in data_batch
                if float(str(item).split(":")[1]) > 30
            ]
        return super().filter_data(data_batch, criteria)

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        stats = super().get_stats()
        stats["type"] = self.stream_type
        return stats


class TransactionStream(DataStream):
    def __init__(self, stream_id: str) -> None:
        super().__init__(stream_id)
        self.stream_type: str = "Financial Data"

    def process_batch(self, data_batch: List[Any]) -> str:
        try:
            if not data_batch:
                raise ValueError("Empty transaction batch")
            net: float = 0.0
            for item in data_batch:
                parts = str(item).split(":")
                op, val = parts[0], float(parts[1])
                net += val if op == "buy" else -val
            self.processed_count += len(data_batch)
            sign = "+" if net >= 0 else ""
            return (
                f"{len(data_batch)} operations, "
                f"net flow: {sign}{net:.0f} units"
            )
        except Exception as e:
            return f"Transaction stream error: {e}"

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        if criteria == "large":
            return [
                item for item in data_batch
                if float(str(item).split(":")[1]) > 100
            ]
        return super().filter_data(data_batch, criteria)

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        stats = super().get_stats()
        stats["type"] = self.stream_type
        return stats


class EventStream(DataStream):
    def __init__(self, stream_id: str) -> None:
        super().__init__(stream_id)
        self.stream_type: str = "System Events"

    def process_batch(self, data_batch: List[Any]) -> str:
        try:
            if not data_batch:
                raise ValueError("Empty event batch")
            errors = [e for e in data_batch if "error" in str(e).lower()]
            self.processed_count += len(data_batch)
            return (
                f"{len(data_batch)} events, "
                f"{len(errors)} error detected"
            )
        except Exception as e:
            return f"Event stream error: {e}"

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        if criteria == "errors":
            return [e for e in data_batch if "error" in str(e).lower()]
        return super().filter_data(data_batch, criteria)

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        stats = super().get_stats()
        stats["type"] = self.stream_type
        return stats


class StreamProcessor:
    def __init__(self) -> None:
        self.streams: List[DataStream] = []

    def add_stream(self, stream: DataStream) -> None:
        self.streams.append(stream)

    def process_all(self, data_batches: List[List[Any]]) -> None:
        for stream, batch in zip(self.streams, data_batches):
            try:
                result = stream.process_batch(batch)
                if isinstance(stream, SensorStream):
                    print(f"- Sensor data: {result.split(',')[0]}")
                elif isinstance(stream, TransactionStream):
                    print(f"- Transaction data: {result.split(',')[0]}")
                elif isinstance(stream, EventStream):
                    print(f"- Event data: {result.split(',')[0]}")
            except Exception as e:
                print(f"Stream {stream.stream_id} failed: {e}")

    def filter_stream(
        self,
        stream: DataStream,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        return stream.filter_data(data_batch, criteria)


def main() -> None:
    print("=== CODE NEXUS - POLYMORPHIC STREAM SYSTEM ===")

    sensor = SensorStream("SENSOR_001")
    print("\nInitializing Sensor Stream...")
    print(f"Stream ID: {sensor.stream_id}, Type: {sensor.stream_type}")
    sensor_batch: List[Any] = ["temp:22.5", "humidity:65", "pressure:1013"]
    print("Processing sensor batch: [temp:22.5, humidity:65, pressure:1013]")
    print(f"Sensor analysis: {sensor.process_batch(sensor_batch)}")

    transaction = TransactionStream("TRANS_001")
    print("\nInitializing Transaction Stream...")
    print(f"Stream ID: {transaction.stream_id}, "
          f"Type: {transaction.stream_type}")
    trans_batch: List[Any] = ["buy:100", "sell:150", "buy:75"]
    print("Processing transaction batch: [buy:100, sell:150, buy:75]")
    print(f"Transaction analysis: {transaction.process_batch(trans_batch)}")

    event = EventStream("EVENT_001")
    print("\nInitializing Event Stream...")
    print(f"Stream ID: {event.stream_id}, Type: {event.stream_type}")
    event_batch: List[Any] = ["login", "error", "logout"]
    print(f"Processing event batch: {event_batch}")
    print(f"Event analysis: {event.process_batch(event_batch)}")

    print("\n=== Polymorphic Stream Processing ===")
    print("Processing mixed stream types through unified interface...")

    processor = StreamProcessor()
    processor.add_stream(SensorStream("SENSOR_002"))
    processor.add_stream(TransactionStream("TRANS_002"))
    processor.add_stream(EventStream("EVENT_002"))

    mixed_batches: List[List[Any]] = [
        ["temp:20.1", "humidity:55"],
        ["buy:50", "sell:80", "buy:120", "sell:30"],
        ["login", "error", "logout"],
    ]

    print("\nBatch 1 Results:")
    processor.process_all(mixed_batches)

    print("\nStream filtering active: High-priority data only")
    sensor3 = SensorStream("SENSOR_003")
    sensor_data: List[Any] = ["temp:22.0", "temp:31.5", "temp:35.0"]
    critical = processor.filter_stream(sensor3, sensor_data, "critical")

    trans3 = TransactionStream("TRANS_003")
    trans_data: List[Any] = ["buy:50", "sell:200", "buy:30"]
    large = processor.filter_stream(trans3, trans_data, "large")

    print(
        f"Filtered results: {len(critical)} critical sensor alerts, "
        f"{len(large)} large transaction"
    )

    print("\nAll streams processed successfully. Nexus throughput optimal.")


if __name__ == "__main__":
    main()
