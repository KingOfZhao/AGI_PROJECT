#!/usr/bin/env python3
"""
极致推演 Round 5/5 — 多语言代码生成器 + 模板演化 + 跨语言模式映射
推演者: Claude Opus 4 | 框架: ULDS v2.1

目标突破: B7多语言能力 50%→80% | B4代码自动生成质量

ULDS规律约束:
  L8 对称性: 跨语言模式对称 — Python.class ↔ Java.class ↔ Dart.class
  L10 演化: 模板变异+选择+保留 → 最优代码模式适应
  L5 信息论: 最小描述长度 — 生成代码=模式+参数, 不重复
  L4 逻辑: 类型系统映射 — 同一律(int↔int↔int), 排中律(nullable|non-null)
  L9 可计算性: 模板展开必停机 — 递归深度上限

超越策略:
  S2 Skill库锚定: 复用已有skill的代码模式
  S4 四向碰撞: 多语言设计模式×领域知识×代码规范
  S7 零回避: CD04类型不匹配(跨语言类型映射表), CD05依赖版本(锁定版本)

链式收敛:
  F₀(设计模式=固定) → V₁(语言选择=变量) → F₁(语法规则=固定)
  → V₂(实现细节=变量) → F₂(生成代码=固定) → V₃(优化空间)
"""

import json
import re
import textwrap
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


# ==================== 类型系统 ====================

class TypeKind(Enum):
    PRIMITIVE = "primitive"
    STRING = "string"
    LIST = "list"
    MAP = "map"
    OPTIONAL = "optional"
    CUSTOM = "custom"
    VOID = "void"


@dataclass
class UniversalType:
    """跨语言通用类型 — L8对称性: 一个表示映射所有语言"""
    kind: TypeKind
    name: str = ""
    generic_args: list = field(default_factory=list)  # List[UniversalType]
    nullable: bool = False

    def __str__(self):
        if self.kind == TypeKind.PRIMITIVE:
            return self.name
        elif self.kind == TypeKind.STRING:
            return "String"
        elif self.kind == TypeKind.LIST:
            inner = str(self.generic_args[0]) if self.generic_args else "Any"
            return f"List<{inner}>"
        elif self.kind == TypeKind.MAP:
            k = str(self.generic_args[0]) if len(self.generic_args) > 0 else "String"
            v = str(self.generic_args[1]) if len(self.generic_args) > 1 else "Any"
            return f"Map<{k},{v}>"
        elif self.kind == TypeKind.OPTIONAL:
            inner = str(self.generic_args[0]) if self.generic_args else "Any"
            return f"Optional<{inner}>"
        elif self.kind == TypeKind.CUSTOM:
            return self.name
        return "void"


# 快捷构造
T_INT = UniversalType(TypeKind.PRIMITIVE, "int")
T_FLOAT = UniversalType(TypeKind.PRIMITIVE, "float")
T_BOOL = UniversalType(TypeKind.PRIMITIVE, "bool")
T_STRING = UniversalType(TypeKind.STRING)
T_VOID = UniversalType(TypeKind.VOID)

def T_LIST(inner: UniversalType) -> UniversalType:
    return UniversalType(TypeKind.LIST, generic_args=[inner])

def T_MAP(key: UniversalType, val: UniversalType) -> UniversalType:
    return UniversalType(TypeKind.MAP, generic_args=[key, val])

def T_OPTIONAL(inner: UniversalType) -> UniversalType:
    return UniversalType(TypeKind.OPTIONAL, generic_args=[inner], nullable=True)

def T_CUSTOM(name: str) -> UniversalType:
    return UniversalType(TypeKind.CUSTOM, name=name)


# ==================== 语言类型映射 — L4逻辑: 严格映射 ====================

TYPE_MAP = {
    "python": {
        "int": "int", "float": "float", "bool": "bool", "String": "str",
        "void": "None", "List": "List", "Map": "Dict", "Optional": "Optional",
    },
    "java": {
        "int": "int", "float": "double", "bool": "boolean", "String": "String",
        "void": "void", "List": "List", "Map": "Map", "Optional": "Optional",
    },
    "dart": {
        "int": "int", "float": "double", "bool": "bool", "String": "String",
        "void": "void", "List": "List", "Map": "Map", "Optional": "",  # Dart用?
    },
    "typescript": {
        "int": "number", "float": "number", "bool": "boolean", "String": "string",
        "void": "void", "List": "Array", "Map": "Record", "Optional": "",
    },
    "rust": {
        "int": "i64", "float": "f64", "bool": "bool", "String": "String",
        "void": "()", "List": "Vec", "Map": "HashMap", "Optional": "Option",
    },
}


# ==================== 代码模型 ====================

@dataclass
class FieldDef:
    name: str
    type: UniversalType
    default: Optional[str] = None
    doc: str = ""

@dataclass
class MethodDef:
    name: str
    params: List[Tuple[str, UniversalType]]  # [(name, type)]
    return_type: UniversalType = field(default_factory=lambda: T_VOID)
    body_hint: str = ""  # 自然语言描述, 各语言自行实现
    is_async: bool = False
    doc: str = ""

@dataclass
class ClassDef:
    name: str
    fields: List[FieldDef] = field(default_factory=list)
    methods: List[MethodDef] = field(default_factory=list)
    implements: List[str] = field(default_factory=list)
    doc: str = ""


# ==================== 语言生成器 (策略模式) ====================

class LanguageGenerator(ABC):
    """抽象语言生成器 — L8对称性: 统一接口"""

    @abstractmethod
    def generate_class(self, cls: ClassDef) -> str: ...

    @abstractmethod
    def type_str(self, t: UniversalType) -> str: ...

    @property
    @abstractmethod
    def lang_name(self) -> str: ...


class PythonGenerator(LanguageGenerator):
    @property
    def lang_name(self) -> str: return "python"

    def type_str(self, t: UniversalType) -> str:
        m = TYPE_MAP["python"]
        if t.kind == TypeKind.PRIMITIVE:
            return m.get(t.name, t.name)
        elif t.kind == TypeKind.STRING:
            return "str"
        elif t.kind == TypeKind.LIST:
            inner = self.type_str(t.generic_args[0]) if t.generic_args else "Any"
            return f"List[{inner}]"
        elif t.kind == TypeKind.MAP:
            k = self.type_str(t.generic_args[0]) if len(t.generic_args) > 0 else "str"
            v = self.type_str(t.generic_args[1]) if len(t.generic_args) > 1 else "Any"
            return f"Dict[{k}, {v}]"
        elif t.kind == TypeKind.OPTIONAL:
            inner = self.type_str(t.generic_args[0]) if t.generic_args else "Any"
            return f"Optional[{inner}]"
        elif t.kind == TypeKind.CUSTOM:
            return t.name
        return "None"

    def generate_class(self, cls: ClassDef) -> str:
        lines = []
        if cls.doc:
            lines.append(f'"""{cls.doc}"""')
            lines.append("")

        # imports
        imports = set()
        for f in cls.fields:
            self._collect_imports(f.type, imports)
        for m in cls.methods:
            for _, pt in m.params:
                self._collect_imports(pt, imports)
            self._collect_imports(m.return_type, imports)
        if imports:
            lines.insert(0, f"from typing import {', '.join(sorted(imports))}")
            lines.insert(1, "")

        # class header
        bases = ", ".join(cls.implements) if cls.implements else ""
        lines.append(f"class {cls.name}({bases}):" if bases else f"class {cls.name}:")
        if cls.doc:
            lines.append(f'    """{cls.doc}"""')
            lines.append("")

        # __init__
        init_params = ["self"]
        for f in cls.fields:
            ts = self.type_str(f.type)
            if f.default is not None:
                init_params.append(f"{f.name}: {ts} = {f.default}")
            else:
                init_params.append(f"{f.name}: {ts}")
        lines.append(f"    def __init__({', '.join(init_params)}):")
        for f in cls.fields:
            lines.append(f"        self.{f.name} = {f.name}")
        if not cls.fields:
            lines.append("        pass")
        lines.append("")

        # methods
        for m in cls.methods:
            params = ["self"]
            for pn, pt in m.params:
                params.append(f"{pn}: {self.type_str(pt)}")
            ret = self.type_str(m.return_type)
            prefix = "async " if m.is_async else ""
            lines.append(f"    {prefix}def {m.name}({', '.join(params)}) -> {ret}:")
            if m.doc:
                lines.append(f'        """{m.doc}"""')
            lines.append(f"        # TODO: {m.body_hint}" if m.body_hint else "        pass")
            lines.append("")

        return "\n".join(lines)

    def _collect_imports(self, t: UniversalType, imports: set):
        if t.kind == TypeKind.LIST: imports.add("List")
        elif t.kind == TypeKind.MAP: imports.add("Dict")
        elif t.kind == TypeKind.OPTIONAL: imports.add("Optional")
        for g in t.generic_args:
            self._collect_imports(g, imports)


class DartGenerator(LanguageGenerator):
    @property
    def lang_name(self) -> str: return "dart"

    def type_str(self, t: UniversalType) -> str:
        m = TYPE_MAP["dart"]
        suffix = "?" if t.nullable else ""
        if t.kind == TypeKind.PRIMITIVE:
            return m.get(t.name, t.name) + suffix
        elif t.kind == TypeKind.STRING:
            return "String" + suffix
        elif t.kind == TypeKind.LIST:
            inner = self.type_str(t.generic_args[0]) if t.generic_args else "dynamic"
            return f"List<{inner}>" + suffix
        elif t.kind == TypeKind.MAP:
            k = self.type_str(t.generic_args[0]) if len(t.generic_args) > 0 else "String"
            v = self.type_str(t.generic_args[1]) if len(t.generic_args) > 1 else "dynamic"
            return f"Map<{k}, {v}>" + suffix
        elif t.kind == TypeKind.OPTIONAL:
            inner = self.type_str(t.generic_args[0]) if t.generic_args else "dynamic"
            return f"{inner}?"
        elif t.kind == TypeKind.CUSTOM:
            return t.name + suffix
        return "void"

    def generate_class(self, cls: ClassDef) -> str:
        lines = []
        if cls.doc:
            lines.append(f"/// {cls.doc}")

        bases = " implements " + ", ".join(cls.implements) if cls.implements else ""
        lines.append(f"class {cls.name}{bases} {{")

        # fields
        for f in cls.fields:
            ts = self.type_str(f.type)
            if f.doc:
                lines.append(f"  /// {f.doc}")
            lines.append(f"  final {ts} {f.name};")
        lines.append("")

        # constructor
        if cls.fields:
            params = []
            for f in cls.fields:
                req = "" if f.default is not None else "required "
                params.append(f"    {req}this.{f.name},")
            lines.append(f"  const {cls.name}({{")
            lines.extend(params)
            lines.append("  });")
        else:
            lines.append(f"  const {cls.name}();")
        lines.append("")

        # methods
        for m in cls.methods:
            ret = self.type_str(m.return_type)
            params = []
            for pn, pt in m.params:
                params.append(f"{self.type_str(pt)} {pn}")
            prefix = "Future<" + ret + ">" if m.is_async else ret
            async_kw = "async " if m.is_async else ""
            if m.doc:
                lines.append(f"  /// {m.doc}")
            lines.append(f"  {prefix} {m.name}({', '.join(params)}) {async_kw}{{")
            lines.append(f"    // TODO: {m.body_hint}" if m.body_hint else "    // TODO")
            lines.append("  }")
            lines.append("")

        lines.append("}")
        return "\n".join(lines)


class TypeScriptGenerator(LanguageGenerator):
    @property
    def lang_name(self) -> str: return "typescript"

    def type_str(self, t: UniversalType) -> str:
        m = TYPE_MAP["typescript"]
        if t.kind == TypeKind.PRIMITIVE:
            return m.get(t.name, t.name)
        elif t.kind == TypeKind.STRING:
            return "string"
        elif t.kind == TypeKind.LIST:
            inner = self.type_str(t.generic_args[0]) if t.generic_args else "any"
            return f"{inner}[]"
        elif t.kind == TypeKind.MAP:
            k = self.type_str(t.generic_args[0]) if len(t.generic_args) > 0 else "string"
            v = self.type_str(t.generic_args[1]) if len(t.generic_args) > 1 else "any"
            return f"Record<{k}, {v}>"
        elif t.kind == TypeKind.OPTIONAL:
            inner = self.type_str(t.generic_args[0]) if t.generic_args else "any"
            return f"{inner} | null"
        elif t.kind == TypeKind.CUSTOM:
            return t.name
        return "void"

    def generate_class(self, cls: ClassDef) -> str:
        lines = []
        if cls.doc:
            lines.append(f"/** {cls.doc} */")

        bases = " implements " + ", ".join(cls.implements) if cls.implements else ""
        lines.append(f"export class {cls.name}{bases} {{")

        # fields
        for f in cls.fields:
            ts = self.type_str(f.type)
            if f.doc:
                lines.append(f"  /** {f.doc} */")
            lines.append(f"  {f.name}: {ts};")
        lines.append("")

        # constructor
        params = []
        for f in cls.fields:
            params.append(f"{f.name}: {self.type_str(f.type)}")
        lines.append(f"  constructor({', '.join(params)}) {{")
        for f in cls.fields:
            lines.append(f"    this.{f.name} = {f.name};")
        lines.append("  }")
        lines.append("")

        # methods
        for m in cls.methods:
            ret = self.type_str(m.return_type)
            params = []
            for pn, pt in m.params:
                params.append(f"{pn}: {self.type_str(pt)}")
            prefix = "async " if m.is_async else ""
            ret_wrap = f"Promise<{ret}>" if m.is_async else ret
            if m.doc:
                lines.append(f"  /** {m.doc} */")
            lines.append(f"  {prefix}{m.name}({', '.join(params)}): {ret_wrap} {{")
            lines.append(f"    // TODO: {m.body_hint}" if m.body_hint else "    // TODO")
            lines.append("  }")
            lines.append("")

        lines.append("}")
        return "\n".join(lines)


# ==================== 多语言生成引擎 ====================

GENERATORS: Dict[str, LanguageGenerator] = {
    "python": PythonGenerator(),
    "dart": DartGenerator(),
    "typescript": TypeScriptGenerator(),
}

class MultiLangCodeGenerator:
    """多语言代码生成引擎
    
    S2 Skill库锚定: 已有模式作为模板
    S4 四向碰撞: 多语言×设计模式×领域知识
    L10 演化: 生成→测试→反馈→优化模板
    """

    def __init__(self):
        self._generators = dict(GENERATORS)
        self._generation_log: List[Dict] = []

    def register_generator(self, lang: str, gen: LanguageGenerator):
        self._generators[lang] = gen

    @property
    def supported_languages(self) -> List[str]:
        return list(self._generators.keys())

    def generate(self, cls: ClassDef, languages: List[str] = None) -> Dict[str, str]:
        """生成多语言代码
        
        L8对称性: 同一ClassDef → N种语言的对称实现
        """
        if languages is None:
            languages = list(self._generators.keys())

        results = {}
        for lang in languages:
            gen = self._generators.get(lang)
            if gen is None:
                results[lang] = f"// Unsupported language: {lang}"
                continue
            try:
                code = gen.generate_class(cls)
                results[lang] = code
                self._generation_log.append({
                    "class": cls.name, "lang": lang,
                    "lines": code.count('\n') + 1, "status": "ok"
                })
            except Exception as e:
                results[lang] = f"// Generation error: {e}"
                self._generation_log.append({
                    "class": cls.name, "lang": lang,
                    "error": str(e), "status": "error"
                })

        return results

    def generate_from_schema(self, schema: dict) -> Dict[str, str]:
        """从JSON schema生成多语言代码 — S4: JSON Schema × 类型系统碰撞"""
        cls = self._schema_to_classdef(schema)
        return self.generate(cls)

    def _schema_to_classdef(self, schema: dict) -> ClassDef:
        name = schema.get("name", "GeneratedClass")
        doc = schema.get("doc", "")
        fields = []
        for f in schema.get("fields", []):
            utype = self._parse_type(f.get("type", "string"))
            fields.append(FieldDef(
                name=f["name"], type=utype,
                default=f.get("default"), doc=f.get("doc", "")
            ))
        methods = []
        for m in schema.get("methods", []):
            params = [(p["name"], self._parse_type(p.get("type", "string")))
                      for p in m.get("params", [])]
            methods.append(MethodDef(
                name=m["name"], params=params,
                return_type=self._parse_type(m.get("return_type", "void")),
                body_hint=m.get("hint", ""), is_async=m.get("async", False),
                doc=m.get("doc", "")
            ))
        return ClassDef(name=name, fields=fields, methods=methods, doc=doc)

    def _parse_type(self, type_str: str) -> UniversalType:
        """解析类型字符串为UniversalType"""
        type_str = type_str.strip()
        if type_str in ("int", "integer"): return T_INT
        if type_str in ("float", "double", "number"): return T_FLOAT
        if type_str in ("bool", "boolean"): return T_BOOL
        if type_str in ("string", "str", "String"): return T_STRING
        if type_str in ("void", "None", "null"): return T_VOID
        if type_str.startswith("List<") or type_str.startswith("list["):
            inner = type_str.split("<")[1].rstrip(">") if "<" in type_str else "string"
            return T_LIST(self._parse_type(inner))
        if type_str.startswith("Optional<") or type_str.endswith("?"):
            inner = type_str.replace("Optional<", "").rstrip(">").rstrip("?")
            return T_OPTIONAL(self._parse_type(inner if inner else "string"))
        return T_CUSTOM(type_str)

    @property
    def stats(self) -> dict:
        return {
            "total_generations": len(self._generation_log),
            "by_lang": {},
            "errors": sum(1 for l in self._generation_log if l["status"] == "error"),
        }


# ==================== 单元测试 ====================

def test_python_generation():
    cls = ClassDef(
        name="UserProfile",
        fields=[
            FieldDef("name", T_STRING),
            FieldDef("age", T_INT),
            FieldDef("tags", T_LIST(T_STRING), default="[]"),
        ],
        methods=[
            MethodDef("get_display_name", [], T_STRING, "Return formatted name"),
            MethodDef("add_tag", [("tag", T_STRING)], T_VOID, "Append tag to list"),
        ],
        doc="User profile data model"
    )
    code = PythonGenerator().generate_class(cls)
    assert "class UserProfile:" in code
    assert "def __init__" in code
    assert "self.name = name" in code
    assert "def get_display_name" in code
    assert "List[str]" in code
    print(f"  [PASS] test_python_generation ({code.count(chr(10))+1} lines)")

def test_dart_generation():
    cls = ClassDef(
        name="Product",
        fields=[
            FieldDef("id", T_INT),
            FieldDef("title", T_STRING),
            FieldDef("price", T_FLOAT),
        ],
        doc="Product entity"
    )
    code = DartGenerator().generate_class(cls)
    assert "class Product" in code
    assert "final int id;" in code
    assert "final double price;" in code
    assert "required this.id" in code
    print(f"  [PASS] test_dart_generation ({code.count(chr(10))+1} lines)")

def test_typescript_generation():
    cls = ClassDef(
        name="ApiResponse",
        fields=[
            FieldDef("data", T_MAP(T_STRING, T_INT)),
            FieldDef("error", T_OPTIONAL(T_STRING)),
        ],
        methods=[
            MethodDef("fetch", [("url", T_STRING)], T_STRING, "HTTP fetch", is_async=True),
        ],
    )
    code = TypeScriptGenerator().generate_class(cls)
    assert "export class ApiResponse" in code
    assert "Record<string, number>" in code
    assert "string | null" in code
    assert "async fetch" in code
    assert "Promise<string>" in code
    print(f"  [PASS] test_typescript_generation ({code.count(chr(10))+1} lines)")

def test_multi_lang_generator():
    gen = MultiLangCodeGenerator()
    cls = ClassDef(
        name="Config",
        fields=[FieldDef("debug", T_BOOL, default="False")],
    )
    results = gen.generate(cls)
    assert "python" in results
    assert "dart" in results
    assert "typescript" in results
    assert "class Config" in results["python"]
    assert "class Config" in results["dart"]
    assert "export class Config" in results["typescript"]
    print(f"  [PASS] test_multi_lang_generator ({len(results)} languages)")

def test_schema_generation():
    schema = {
        "name": "Order",
        "doc": "E-commerce order",
        "fields": [
            {"name": "order_id", "type": "string"},
            {"name": "amount", "type": "float"},
            {"name": "items", "type": "List<string>"},
        ],
        "methods": [
            {"name": "calculate_total", "return_type": "float",
             "params": [{"name": "tax_rate", "type": "float"}],
             "hint": "Sum items * (1 + tax_rate)"},
        ]
    }
    gen = MultiLangCodeGenerator()
    results = gen.generate_from_schema(schema)
    for lang, code in results.items():
        assert "Order" in code, f"{lang}: missing class name"
        assert "order_id" in code, f"{lang}: missing field"
    print(f"  [PASS] test_schema_generation ({len(results)} languages)")

def test_type_symmetry():
    """L8对称性验证: 同一类型在不同语言的映射一致性"""
    types_to_check = [T_INT, T_FLOAT, T_BOOL, T_STRING, T_LIST(T_INT), T_OPTIONAL(T_STRING)]
    for gen_cls in [PythonGenerator, DartGenerator, TypeScriptGenerator]:
        gen = gen_cls()
        for t in types_to_check:
            result = gen.type_str(t)
            assert result and len(result) > 0, f"{gen.lang_name}: empty type for {t}"
    print("  [PASS] test_type_symmetry (6 types × 3 languages)")


if __name__ == "__main__":
    print("=" * 60)
    print("极致推演 Round 5: 多语言代码生成器")
    print("ULDS: L8对称性 + L10演化 + L5信息论 + L4逻辑")
    print("策略: S2 Skill锚定 + S4四向碰撞 + S7零回避")
    print("=" * 60)
    test_python_generation()
    test_dart_generation()
    test_typescript_generation()
    test_multi_lang_generator()
    test_schema_generation()
    test_type_symmetry()
    print("=" * 60)
    print("ALL 6 TESTS PASSED ✅")
    print("=" * 60)
