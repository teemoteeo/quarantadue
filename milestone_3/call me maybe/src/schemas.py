"""Pydantic schemas describing the I/O contracts for function calling."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonScalarType = Literal["number", "integer", "string", "boolean"]


class ParameterSpec(BaseModel):
    """Schema entry describing a single function parameter."""

    model_config = ConfigDict(extra="forbid")

    type: JsonScalarType


class ReturnSpec(BaseModel):
    """Schema entry describing the return value of a function."""

    model_config = ConfigDict(extra="forbid")

    type: JsonScalarType


class FunctionDefinition(BaseModel):
    """A callable function exposed to the language model."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    parameters: dict[str, ParameterSpec]
    returns: ReturnSpec


class TestPrompt(BaseModel):
    """A natural-language prompt to turn into a function call."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1)


class FunctionCallResult(BaseModel):
    """The result of resolving a prompt into a concrete function call."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    name: str
    parameters: dict[str, Any]
