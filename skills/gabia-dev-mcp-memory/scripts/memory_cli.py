#!/usr/bin/env python3
import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v or None


def _resolve_memory_path(override: str | None) -> Path:
    raw = (override or _env("MEMORY_FILE_PATH") or "memory.json").strip()
    p = Path(raw)
    return p if p.is_absolute() else Path.cwd() / p


def _read_input_json(path: str | None) -> dict:
    if path:
        data = Path(path).read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            raise SystemExit("[ERROR] Provide --input <json-file> or pipe JSON via stdin.")
        data = sys.stdin.read()
    obj = json.loads(data)
    if not isinstance(obj, dict):
        raise SystemExit("[ERROR] Input JSON must be an object.")
    return obj


@dataclass
class Entity:
    name: str
    entityType: str
    observations: list[str]


@dataclass
class Relation:
    from_: str
    to: str
    relationType: str


def _load_graph(memory_file: Path) -> tuple[list[Entity], list[Relation]]:
    if not memory_file.exists():
        return [], []

    entities: list[Entity] = []
    relations: list[Relation] = []
    for line in memory_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        t = obj.get("type")
        if t == "entity":
            name = obj.get("name")
            entity_type = obj.get("entityType")
            observations = obj.get("observations") or []
            if isinstance(name, str) and isinstance(entity_type, str) and isinstance(observations, list):
                entities.append(
                    Entity(
                        name=name,
                        entityType=entity_type,
                        observations=[x for x in observations if isinstance(x, str)],
                    )
                )
        elif t == "relation":
            from_ = obj.get("from")
            to = obj.get("to")
            relation_type = obj.get("relationType")
            if isinstance(from_, str) and isinstance(to, str) and isinstance(relation_type, str):
                relations.append(Relation(from_=from_, to=to, relationType=relation_type))
    return entities, relations


def _save_graph(memory_file: Path, entities: list[Entity], relations: list[Relation]) -> None:
    memory_file.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for e in entities:
        lines.append(
            json.dumps(
                {
                    "type": "entity",
                    "name": e.name,
                    "entityType": e.entityType,
                    "observations": e.observations,
                },
                ensure_ascii=False,
            )
        )
    for r in relations:
        lines.append(
            json.dumps(
                {
                    "type": "relation",
                    "from": r.from_,
                    "to": r.to,
                    "relationType": r.relationType,
                },
                ensure_ascii=False,
            )
        )
    memory_file.write_text("\n".join(lines), encoding="utf-8")


def _graph_to_json(entities: list[Entity], relations: list[Relation]) -> dict:
    return {
        "entities": [
            {"name": e.name, "entityType": e.entityType, "observations": list(e.observations)} for e in entities
        ],
        "relations": [{"from": r.from_, "to": r.to, "relationType": r.relationType} for r in relations],
    }


def cmd_create_entities(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    data = _read_input_json(args.input)
    incoming = data.get("entities") or []
    if not isinstance(incoming, list):
        raise SystemExit("[ERROR] 'entities' must be an array.")

    entities, relations = _load_graph(memory_file)
    existing = {e.name for e in entities}
    created: list[Entity] = []
    for it in incoming:
        if not isinstance(it, dict):
            continue
        name = it.get("name")
        entity_type = it.get("entityType")
        observations = it.get("observations") or []
        if not (isinstance(name, str) and isinstance(entity_type, str) and isinstance(observations, list)):
            continue
        if name in existing:
            continue
        e = Entity(name=name, entityType=entity_type, observations=[x for x in observations if isinstance(x, str)])
        entities.append(e)
        created.append(e)
        existing.add(name)

    _save_graph(memory_file, entities, relations)
    print(json.dumps([{"name": e.name, "entityType": e.entityType, "observations": e.observations} for e in created], ensure_ascii=False))


def cmd_create_relations(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    data = _read_input_json(args.input)
    incoming = data.get("relations") or []
    if not isinstance(incoming, list):
        raise SystemExit("[ERROR] 'relations' must be an array.")

    entities, relations = _load_graph(memory_file)
    existing = {(r.from_, r.to, r.relationType) for r in relations}
    created: list[Relation] = []
    for it in incoming:
        if not isinstance(it, dict):
            continue
        from_ = it.get("from")
        to = it.get("to")
        relation_type = it.get("relationType")
        if not (isinstance(from_, str) and isinstance(to, str) and isinstance(relation_type, str)):
            continue
        key = (from_, to, relation_type)
        if key in existing:
            continue
        r = Relation(from_=from_, to=to, relationType=relation_type)
        relations.append(r)
        created.append(r)
        existing.add(key)

    _save_graph(memory_file, entities, relations)
    print(json.dumps([{"from": r.from_, "to": r.to, "relationType": r.relationType} for r in created], ensure_ascii=False))


def cmd_add_observations(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    data = _read_input_json(args.input)
    incoming = data.get("observations") or []
    if not isinstance(incoming, list):
        raise SystemExit("[ERROR] 'observations' must be an array.")

    entities, relations = _load_graph(memory_file)
    by_name = {e.name: e for e in entities}
    results: list[dict] = []
    for it in incoming:
        if not isinstance(it, dict):
            continue
        entity_name = it.get("entityName")
        contents = it.get("contents") or []
        if not (isinstance(entity_name, str) and isinstance(contents, list)):
            continue
        entity = by_name.get(entity_name)
        if entity is None:
            raise SystemExit(f"[ERROR] Entity with name '{entity_name}' not found")
        new_ones = [c for c in contents if isinstance(c, str) and c not in entity.observations]
        entity.observations.extend(new_ones)
        results.append({"entityName": entity_name, "contents": new_ones})

    _save_graph(memory_file, entities, relations)
    print(json.dumps(results, ensure_ascii=False))


def cmd_delete_entities(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    data = _read_input_json(args.input)
    names = data.get("entityNames") or []
    if not isinstance(names, list) or not all(isinstance(x, str) for x in names):
        raise SystemExit("[ERROR] 'entityNames' must be an array of strings.")

    entities, relations = _load_graph(memory_file)
    names_set = set(names)
    entities = [e for e in entities if e.name not in names_set]
    relations = [r for r in relations if (r.from_ not in names_set and r.to not in names_set)]
    _save_graph(memory_file, entities, relations)
    print(json.dumps({"success": True}, ensure_ascii=False))


def cmd_delete_observations(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    data = _read_input_json(args.input)
    deletions = data.get("deletions") or []
    if not isinstance(deletions, list):
        raise SystemExit("[ERROR] 'deletions' must be an array.")

    entities, relations = _load_graph(memory_file)
    by_name = {e.name: e for e in entities}
    for it in deletions:
        if not isinstance(it, dict):
            continue
        entity_name = it.get("entityName")
        obs = it.get("observations") or []
        if not (isinstance(entity_name, str) and isinstance(obs, list)):
            continue
        entity = by_name.get(entity_name)
        if entity is None:
            continue
        remove = {x for x in obs if isinstance(x, str)}
        entity.observations = [o for o in entity.observations if o not in remove]

    _save_graph(memory_file, entities, relations)
    print(json.dumps({"success": True}, ensure_ascii=False))


def cmd_delete_relations(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    data = _read_input_json(args.input)
    incoming = data.get("relations") or []
    if not isinstance(incoming, list):
        raise SystemExit("[ERROR] 'relations' must be an array.")

    to_delete: set[tuple[str, str, str]] = set()
    for it in incoming:
        if not isinstance(it, dict):
            continue
        from_ = it.get("from")
        to = it.get("to")
        relation_type = it.get("relationType")
        if isinstance(from_, str) and isinstance(to, str) and isinstance(relation_type, str):
            to_delete.add((from_, to, relation_type))

    entities, relations = _load_graph(memory_file)
    relations = [r for r in relations if (r.from_, r.to, r.relationType) not in to_delete]
    _save_graph(memory_file, entities, relations)
    print(json.dumps({"success": True}, ensure_ascii=False))


def cmd_read_graph(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    entities, relations = _load_graph(memory_file)
    print(json.dumps(_graph_to_json(entities, relations), ensure_ascii=False))


def cmd_search_nodes(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    q = args.query.lower()
    entities, relations = _load_graph(memory_file)
    filtered = [
        e
        for e in entities
        if q in e.name.lower() or q in e.entityType.lower() or any(q in o.lower() for o in e.observations)
    ]
    names = {e.name for e in filtered}
    filtered_rel = [r for r in relations if r.from_ in names and r.to in names]
    print(json.dumps(_graph_to_json(filtered, filtered_rel), ensure_ascii=False))


def cmd_open_nodes(args: argparse.Namespace) -> None:
    memory_file = _resolve_memory_path(args.memory_file)
    names = set(args.names)
    entities, relations = _load_graph(memory_file)
    filtered = [e for e in entities if e.name in names]
    included = {e.name for e in filtered}
    filtered_rel = [r for r in relations if r.from_ in included and r.to in included]
    print(json.dumps(_graph_to_json(filtered, filtered_rel), ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Knowledge Graph (Memory) CLI (no MCP required)")
    p.add_argument("--memory-file", help="Override MEMORY_FILE_PATH")
    sub = p.add_subparsers(dest="cmd", required=True)

    ce = sub.add_parser("create-entities", help="Create entities (JSON input: {entities:[...]})")
    ce.add_argument("--input", help="JSON file path (or stdin)")
    ce.set_defaults(func=cmd_create_entities)

    cr = sub.add_parser("create-relations", help="Create relations (JSON input: {relations:[...]})")
    cr.add_argument("--input", help="JSON file path (or stdin)")
    cr.set_defaults(func=cmd_create_relations)

    ao = sub.add_parser("add-observations", help="Add observations (JSON input: {observations:[...]})")
    ao.add_argument("--input", help="JSON file path (or stdin)")
    ao.set_defaults(func=cmd_add_observations)

    de = sub.add_parser("delete-entities", help="Delete entities (JSON input: {entityNames:[...]})")
    de.add_argument("--input", help="JSON file path (or stdin)")
    de.set_defaults(func=cmd_delete_entities)

    do = sub.add_parser("delete-observations", help="Delete observations (JSON input: {deletions:[...]})")
    do.add_argument("--input", help="JSON file path (or stdin)")
    do.set_defaults(func=cmd_delete_observations)

    dr = sub.add_parser("delete-relations", help="Delete relations (JSON input: {relations:[...]})")
    dr.add_argument("--input", help="JSON file path (or stdin)")
    dr.set_defaults(func=cmd_delete_relations)

    rg = sub.add_parser("read-graph", help="Read full graph")
    rg.set_defaults(func=cmd_read_graph)

    sn = sub.add_parser("search-nodes", help="Search nodes by query")
    sn.add_argument("--query", required=True)
    sn.set_defaults(func=cmd_search_nodes)

    on = sub.add_parser("open-nodes", help="Open nodes by names")
    on.add_argument("--names", nargs="+", required=True)
    on.set_defaults(func=cmd_open_nodes)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

