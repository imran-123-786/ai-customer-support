"""
SupportAgent Tool Registry with typed Pydantic validation, permissions, and logging.
"""
from __future__ import annotations

import inspect
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ConfigDict
from support_agent.database.repository import repo
from support_agent.models.schemas import PermissionLevel, ToolCallRecord, ToolResultRecord


class ToolDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    permission: PermissionLevel
    parameters_schema: Dict[str, Any]
    input_model: Optional[Type[BaseModel]] = None
    output_model: Optional[Type[BaseModel]] = None


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        permission: PermissionLevel = PermissionLevel.READ_ONLY,
        input_model: Optional[Type[BaseModel]] = None,
        output_model: Optional[Type[BaseModel]] = None,
    ):
        """Decorator to register a tool function."""
        def decorator(func: Callable):
            schema = {}
            if input_model:
                schema = input_model.model_json_schema()
            else:
                sig = inspect.signature(func)
                schema = {
                    "type": "object",
                    "properties": {
                        param: {"type": "string"} for param in sig.parameters if param not in ("self", "context")
                    },
                }

            self._tools[name] = func
            self._definitions[name] = ToolDefinition(
                name=name,
                description=description,
                permission=permission,
                parameters_schema=schema,
                input_model=input_model,
                output_model=output_model,
            )
            return func

        return decorator

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        return self._definitions.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._definitions.values())

    def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        run_id: Optional[str] = None,
        user_role: str = "customer",
    ) -> ToolResultRecord:
        """Validate permissions, validate input schema, execute, record latency, and log."""
        call_id = f"call-{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        if tool_name not in self._tools:
            err = f"Tool '{tool_name}' not found in registry."
            repo.log_tool_call(call_id, run_id, tool_name, args, None, 0.0, False, err)
            return ToolResultRecord(call_id=call_id, tool_name=tool_name, result=None, success=False, error_message=err)

        defn = self._definitions[tool_name]

        # Permission check: SENSITIVE tools require verification or agent/customer context
        # In a support system, sensitive tools like refund creation are validated
        if defn.permission == PermissionLevel.SENSITIVE and user_role == "unauthorized":
            err = f"Permission denied for sensitive tool '{tool_name}'."
            repo.log_tool_call(call_id, run_id, tool_name, args, None, 0.0, False, err)
            return ToolResultRecord(call_id=call_id, tool_name=tool_name, result=None, success=False, error_message=err)

        # Validate arguments against Pydantic input model if provided
        validated_args = args
        if defn.input_model:
            try:
                model_inst = defn.input_model(**args)
                validated_args = model_inst.model_dump()
            except Exception as e:
                err = f"Input validation failed for {tool_name}: {str(e)}"
                repo.log_tool_call(call_id, run_id, tool_name, args, None, 0.0, False, err)
                return ToolResultRecord(call_id=call_id, tool_name=tool_name, result=None, success=False, error_message=err)

        try:
            func = self._tools[tool_name]
            raw_result = func(**validated_args)

            # Validate output with Pydantic output model if provided
            final_result = raw_result
            if defn.output_model and isinstance(raw_result, dict):
                try:
                    final_result = defn.output_model(**raw_result).model_dump()
                except Exception:
                    pass

            latency_ms = round((time.time() - start_time) * 1000, 2)
            repo.log_tool_call(call_id, run_id, tool_name, validated_args, final_result, latency_ms, True, None)
            return ToolResultRecord(call_id=call_id, tool_name=tool_name, result=final_result, success=True)
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            err = f"Execution error in {tool_name}: {str(e)}"
            repo.log_tool_call(call_id, run_id, tool_name, validated_args, None, latency_ms, False, err)
            return ToolResultRecord(call_id=call_id, tool_name=tool_name, result=None, success=False, error_message=err)


registry = ToolRegistry()
