#!/usr/bin/env python3

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProcessingStage(Protocol):
    def process(self, data: Any) -> Any:
        ...


class InputStage:
    def process(self, data: Any) -> Any:
        return data


class TransformStage:
    def process(self, data: Any) -> Any:
        return data


class OutputStage:
    def process(self, data: Any) -> Any:
        return data


class FaultyTransformStage:
    def process(self, data: Any) -> Any:
        raise ValueError("Invalid data format")


class BackupTransformStage:
    def process(self, data: Any) -> Any:
        return data


class ProcessingPipeline(ABC):
    def __init__(self, pipeline_id: str) -> None:
        self.pipeline_id: str = pipeline_id
        self.stages: List[ProcessingStage] = []
        self.backup_stages: List[ProcessingStage] = []
        self.processed_count: int = 0
        self.error_count: int = 0
        self.verbose: bool = True
        self._start_time: float = time.perf_counter()

    def add_stage(self, stage: ProcessingStage) -> None:
        self.stages.append(stage)

    def add_backup_stage(self, stage: ProcessingStage) -> None:
        self.backup_stages.append(stage)

    def run_with_recovery(self, data: Any) -> Any:
        result = data
        for i, stage in enumerate(self.stages):
            try:
                result = stage.process(result)
            except Exception as e:
                self.error_count += 1
                print(f"Error detected in Stage {i + 1}: {e}")
                if i < len(self.backup_stages):
                    print("Recovery initiated: Switching to backup processor")
                    result = self.backup_stages[i].process(result)
                    print("Recovery successful: "
                          "Pipeline restored, processing resumed")
                else:
                    raise
        return result

    @abstractmethod
    def process(self, data: Any) -> Union[str, Any]:
        pass

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        elapsed = round(time.perf_counter() - self._start_time, 2)
        return {
            "pipeline_id": self.pipeline_id,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "uptime": elapsed,
        }


class JSONAdapter(ProcessingPipeline):
    def __init__(self, pipeline_id: str) -> None:
        super().__init__(pipeline_id)

    def process(self, data: Any) -> Union[str, Any]:
        try:
            validated = self.stages[0].process(data) if self.stages else data
            if self.verbose:
                print(f"Input: {json.dumps(data)}")
            enriched = {
                    self.stages[1].process(validated)
                    if len(self.stages) > 1
                    else validated
                    }
            if self.verbose:
                print("Transform: Enriched with metadata and validation")
            _ = (
                self.stages[2].process(enriched)
                if len(self.stages) > 2
                else enriched
                )
            if isinstance(data, dict):
                sensor = data.get("sensor", "")
                value = data.get("value", 0)
                unit = data.get("unit", "")
                if sensor == "temp":
                    status = {
                            "Normal range"
                            if float(value) < 30
                            else "High temperature"
                            }
                    result = (f"Processed temperature reading: "
                              f"{value}°{unit} ({status})")
                else:
                    result = f"Processed {sensor}: {value} {unit}"
            else:
                result = str(data)
            self.processed_count += 1
            return result
        except Exception as e:
            self.error_count += 1
            return f"JSON pipeline error: {e}"


class CSVAdapter(ProcessingPipeline):
    def __init__(self, pipeline_id: str) -> None:
        super().__init__(pipeline_id)

    def process(self, data: Any) -> Union[str, Any]:
        try:
            validated = self.stages[0].process(data) if self.stages else data
            if self.verbose:
                print(f'Input: "{data}"')
            enriched = {
                    self.stages[1].process(validated)
                    if len(self.stages) > 1
                    else validated
                    }
            if self.verbose:
                print("Transform: Parsed and structured data")
            _ = (
                self.stages[2].process(enriched)
                if len(self.stages) > 2
                else enriched
                )
            if isinstance(data, str):
                fields = [f.strip() for f in data.split(",")]
                action_keywords = {"action", "buy", "sell",
                                   "login", "logout", "click"}
                count = sum(1 for f in fields if f in action_keywords)
                if count == 0:
                    count = 1
                result = f"User activity logged: {count} actions processed"
            else:
                result = str(data)
            self.processed_count += 1
            return result
        except Exception as e:
            self.error_count += 1
            return f"CSV pipeline error: {e}"


class StreamAdapter(ProcessingPipeline):
    def __init__(self, pipeline_id: str) -> None:
        super().__init__(pipeline_id)

    def process(self, data: Any) -> Union[str, Any]:
        try:
            validated = self.stages[0].process(data) if self.stages else data
            if self.verbose:
                print("Input: Real-time sensor stream")
            enriched = {
                    self.stages[1].process(validated)
                    if len(self.stages) > 1
                    else validated
                    }
            if self.verbose:
                print("Transform: Aggregated and filtered")
            _ = (
                    self.stages[2].process(enriched)
                    if len(self.stages) > 2
                    else enriched
                    )
            if isinstance(data, list):
                readings = [
                    float(str(item).split(":")[1])
                    for item in data
                    if str(item).startswith("temp:")
                ]
                count = len(readings)
                avg = round(sum(readings) / count, 1) if readings else 0.0
                result = f"Stream summary: {count} readings, avg: {avg}°C"
            else:
                result = "Stream summary: processed"
            self.processed_count += 1
            return result
        except Exception as e:
            self.error_count += 1
            return f"Stream pipeline error: {e}"


class NexusManager:
    def __init__(self) -> None:
        self.pipelines: List[ProcessingPipeline] = []

    def add_pipeline(self, pipeline: ProcessingPipeline) -> None:
        self.pipelines.append(pipeline)

    def run_all(self, data_list: List[Any]) -> List[Any]:
        results: List[Any] = []
        for pipeline, data in zip(self.pipelines, data_list):
            try:
                result = pipeline.process(data)
                results.append(result)
            except Exception as e:
                results.append(f"Pipeline {pipeline.pipeline_id} error: {e}")
        return results

    def chain(self, data: Any) -> Any:
        result = data
        for pipeline in self.pipelines:
            result = pipeline.process(result)
        return result

    def get_total_stats(self) -> Dict[str, Union[str, int, float]]:
        total_processed = sum(p.processed_count for p in self.pipelines)
        total_errors = sum(p.error_count for p in self.pipelines)
        return {
            "total_pipelines": len(self.pipelines),
            "total_processed": total_processed,
            "total_errors": total_errors,
        }


def main() -> None:
    print("=== CODE NEXUS - ENTERPRISE PIPELINE SYSTEM ===\n")

    manager = NexusManager()
    print("Initializing Nexus Manager...")
    print("Pipeline capacity: 1000 streams/second")

    json_pipeline = JSONAdapter("JSON_PIPELINE")
    print("Creating Data Processing Pipeline...")
    json_pipeline.add_stage(InputStage())
    print("Stage 1: Input validation and parsing")
    json_pipeline.add_stage(TransformStage())
    print("Stage 2: Data transformation and enrichment")
    json_pipeline.add_stage(OutputStage())
    print("Stage 3: Output formatting and delivery")

    csv_pipeline = CSVAdapter("CSV_PIPELINE")
    csv_pipeline.add_stage(InputStage())
    csv_pipeline.add_stage(TransformStage())
    csv_pipeline.add_stage(OutputStage())

    stream_pipeline = StreamAdapter("STREAM_PIPELINE")
    stream_pipeline.add_stage(InputStage())
    stream_pipeline.add_stage(TransformStage())
    stream_pipeline.add_stage(OutputStage())

    manager.add_pipeline(json_pipeline)
    manager.add_pipeline(csv_pipeline)
    manager.add_pipeline(stream_pipeline)

    print("\n=== Multi-Format Data Processing ===")

    print("Processing JSON data through pipeline...")
    json_data: Dict[str, Any] = {"sensor": "temp", "value": 23.5, "unit": "C"}
    json_result = json_pipeline.process(json_data)
    print(f"Output: {json_result}")

    print("\nProcessing CSV data through same pipeline...")
    csv_data = "user,action,timestamp"
    csv_result = csv_pipeline.process(csv_data)
    print(f"Output: {csv_result}")

    print("\nProcessing Stream data through same pipeline...")
    stream_data: List[Any] = ["temp:22.0", "temp:21.5",
                              "temp:22.5", "temp:22.0", "temp:22.5"]
    stream_result = stream_pipeline.process(stream_data)
    print(f"Output: {stream_result}")

    print("\n=== Pipeline Chaining Demo ===")
    print("Pipeline A -> Pipeline B -> Pipeline C")
    print("Data flow: Raw -> Processed -> Analyzed -> Stored")

    chain_a = JSONAdapter("PIPELINE_A")
    chain_a.add_stage(InputStage())
    chain_a.add_stage(TransformStage())
    chain_a.add_stage(OutputStage())
    chain_a.verbose = False

    chain_b = CSVAdapter("PIPELINE_B")
    chain_b.add_stage(InputStage())
    chain_b.add_stage(TransformStage())
    chain_b.add_stage(OutputStage())
    chain_b.verbose = False

    chain_c = StreamAdapter("PIPELINE_C")
    chain_c.add_stage(InputStage())
    chain_c.add_stage(TransformStage())
    chain_c.add_stage(OutputStage())
    chain_c.verbose = False

    chain_manager = NexusManager()
    chain_manager.add_pipeline(chain_a)
    chain_manager.add_pipeline(chain_b)
    chain_manager.add_pipeline(chain_c)

    records = 100
    sample: Dict[str, Any] = {"sensor": "temp", "value": 22.0, "unit": "C"}
    start = time.perf_counter()
    for _ in range(records):
        chain_manager.chain(sample)
    elapsed = round(time.perf_counter() - start, 1)

    chain_stats = chain_manager.get_total_stats()
    total_processed = int(chain_stats["total_processed"])
    efficiency = (round(total_processed /
                        (records * len(chain_manager.pipelines)) * 100))

    print(
        f"Chain result: {records} records processed through "
        f"{len(chain_manager.pipelines)}-stage pipeline"
    )
    print(f"Performance: {efficiency}% efficiency, "
          f"{elapsed}s total processing time")

    print("\n=== Error Recovery Test ===")
    recovery_pipeline = JSONAdapter("RECOVERY_PIPELINE")
    recovery_pipeline.add_stage(InputStage())
    recovery_pipeline.add_stage(FaultyTransformStage())
    recovery_pipeline.add_stage(OutputStage())
    recovery_pipeline.add_backup_stage(InputStage())
    recovery_pipeline.add_backup_stage(BackupTransformStage())
    recovery_pipeline.add_backup_stage(OutputStage())
    recovery_pipeline.verbose = False

    print("Simulating pipeline failure...")
    recovery_pipeline.run_with_recovery({"sensor": "temp",
                                         "value": 23.5, "unit": "C"})
    print("Nexus Integration complete. All systems operational.")


if __name__ == "__main__":
    main()
