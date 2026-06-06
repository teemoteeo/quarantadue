"""Pydantic schemas describing the function-calling I/O contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonScalarType = Literal["number", "integer", "string", "boolean"]


class ParameterSpec(BaseModel):
    """Schema entry describing a single function parameter."""

    model_config = ConfigDict(extra="forbid")

    type: JsonScalarType


class ReturnSpec(BaseModel):
    """Schema entry describing a function return value."""

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
    """A natural-language prompt to be resolved into a function call."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1)


class FunctionCallResult(BaseModel):
    """The outcome of resolving a prompt to a concrete function invocation."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    name: str
    parameters: dict[str, Any]
