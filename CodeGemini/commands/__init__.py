#!/usr/bin/env python3
"""
CodeGemini Commands Module

This module provides:
1. CommandRegistry - Command registration and execution system
2. CommandTemplate - Command template data structure
3. TemplateEngine - Template engine (variable interpolation, conditionals, loops)
4. BuiltinCommands - Built-in command collection
5. MarkdownCommandLoader - Markdown command loader (M-6 feature)

Quick usage:

from CodeGemini.commands import (
    CommandRegistry,
    MarkdownCommandLoader,
    BuiltinCommands
)

# 1. Create registry
registry = CommandRegistry()

# 2. Register built-in commands
BuiltinCommands.register_all(registry)

# 3. Load Markdown custom commands
loader = MarkdownCommandLoader(registry=registry)
loader.scan_and_load()

# 4. Execute command
result = registry.execute_command("my-command", args={"param": "value"})
"""

# Core classes
from .registry import (
    CommandRegistry,
    CommandTemplate,
    CommandType,
    CommandResult
)

# Template engine
from .templates import (
    TemplateEngine,
    Template,
    TemplateLibrary
)

# Built-in commands
from .builtin import BuiltinCommands

# Markdown loader (M-6 feature)
from .loader import (
    MarkdownCommandLoader,
    CommandFile
)

__all__ = [
    # Registry
    'CommandRegistry',
    'CommandTemplate',
    'CommandType',
    'CommandResult',

    # Templates
    'TemplateEngine',
    'Template',
    'TemplateLibrary',

    # Builtin
    'BuiltinCommands',

    # Loader (M-6)
    'MarkdownCommandLoader',
    'CommandFile',
]

__version__ = '1.0.0'
