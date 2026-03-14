from __future__ import annotations

import os
from pathlib import Path

import click

from specanopy.llm import extract_json, get_gemini_client
from specanopy.types import SpecanopyConfig


def generate_specs_from_code(src_dir: Path, specs_dir: Path, config: SpecanopyConfig, granularity: str = "auto") -> None:
    """Read a codebase and use the LLM to write spec files."""
    click.echo(f"Analyzing codebase in {src_dir}...")
    client = get_gemini_client()

    # 1. Read files
    code_files = []
    ignore_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", ".specanopy", "ui", "ui_dist", "dist", "build"}
    
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith((".py", ".js", ".ts", ".go", ".java", ".json", ".yaml", ".md")):
                path = Path(root) / file
                try:
                    content = path.read_text("utf-8")
                    code_files.append({"path": str(path.relative_to(src_dir)), "content": content})
                except UnicodeDecodeError:
                    pass

    if not code_files:
        click.echo(f"No valid source files found in {src_dir}.")
        return

    code_text = ""
    for cf in code_files:
        code_text += f"\n--- FILE: {cf['path']} ---\n{cf['content']}\n"

    # Step 2: Auto-Generate the Migration Skill
    click.echo("Generating migration.skill.md (Architectural context)...")
    skill_prompt = f"""You are an expert software architect. Analyze the following codebase and write a markdown document detailing its architectural patterns, domain boundaries, and coding conventions. This document will be used to instruct AI agents on how to migrate this logic to a new codebase, so be extremely specific about how the system maps inputs to outputs, external services, and abstractions.

Do NOT include markdown language fences like ````markdown` around your total output, just raw markdown.

Codebase:
{code_text}
"""
    try:
        skill_resp = client.models.generate_content(
            model=config.model,
            contents=skill_prompt,
        )
        content = skill_resp.text
        if content.startswith("```markdown"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        elif content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
            
        skill_path = specs_dir / "skills" / "migration.skill.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(content.strip(), "utf-8")
        click.echo(f"  Created {skill_path.relative_to(specs_dir.parent)}")
    except Exception as e:
        click.echo(f"Warning: Failed to generate migration.skill.md: {e}")


    if granularity == "file":
        _extract_file_by_file(client, code_files, specs_dir, config)
    else:
        _extract_auto(client, code_text, specs_dir, config)


def _extract_auto(client, code_text: str, specs_dir: Path, config: SpecanopyConfig) -> None:
    click.echo("Sending payload to LLM to extract contracts...")

    contract_prompt = f"""
You are an expert systems architect. Your goal is to analyze the following codebase and extract its core data models, schemas, and API definitions into Markdown specs.

The output must be a JSON array of objects, where each object has a 'path' (under 'contracts/') and 'content' (the markdown spec with YAML frontmatter).

Required Frontmatter for each spec:
---
id: contracts/<name>
version: 1.0.0
status: approved
---

Codebase:
{code_text}

Output ONLY valid JSON containing the array of spec objects.
"""
    
    response = client.models.generate_content(
        model=config.model,
        contents=contract_prompt,
    )
    
    try:
        contracts = extract_json(response.text)
    except Exception as e:
        click.ClickException(f"Failed to parse contracts from LLM: {e}\n\nResponse:\n{response.text}")
        return

    for c in contracts:
        spec_path = specs_dir / c["path"]
        if not spec_path.name.endswith(".spec.md"):
            spec_path = spec_path.with_name(spec_path.name + ".spec.md")
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(c["content"], "utf-8")
        click.echo(f"  Created {c['path']}")

    click.echo("Extracting behaviors and dependencies...")

    contract_summary = "\n".join([f"- {c['path']}" for c in contracts])
    
    behavior_prompt = f"""
You are an expert systems architect. Analyze the codebase again. 
Extract the business logic, features, and workflows into Markdown specs.

You MUST link these behaviors to the contracts you generated earlier by using the `depends_on` array in the frontmatter.

Existing Contracts:
{contract_summary}

Required Frontmatter for each spec:
---
id: behaviors/<name>
version: 1.0.0
status: approved
parent: behaviors
depends_on:
  - contracts/<relevant_contract>
---

Codebase:
{code_text}

Output ONLY valid JSON containing the array of spec objects (path under 'behaviors/', and content).
"""

    response2 = client.models.generate_content(
        model=config.model,
        contents=behavior_prompt,
    )

    try:
        behaviors = extract_json(response2.text)
    except Exception as e:
        click.ClickException(f"Failed to parse behaviors from LLM: {e}\n\nResponse:\n{response2.text}")
        return

    for b in behaviors:
        spec_path = specs_dir / b["path"]
        if not spec_path.name.endswith(".spec.md"):
            spec_path = spec_path.with_name(spec_path.name + ".spec.md")
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(b["content"], "utf-8")
        click.echo(f"  Created {b['path']}")

    click.echo(f"\nExtraction complete! Initialized {len(contracts) + len(behaviors)} specs in {specs_dir}.")


def _extract_file_by_file(client, code_files: list[dict[str, str]], specs_dir: Path, config: SpecanopyConfig) -> None:
    click.echo(f"Extracting 1:1 specs for {len(code_files)} files...")
    all_paths = [cf['path'] for cf in code_files]
    paths_list = "\n".join([f"- {p}" for p in all_paths])

    for cf in code_files:
        click.echo(f"  Processing {cf['path']}...")
        base_id = Path(cf['path']).with_suffix('').as_posix()
        
        prompt = f"""You are an expert systems architect. Convert the following source file into a single Specanopy Markdown spec.

Project File List (for reference when creating depends_on links):
{paths_list}

Source File: {cf['path']}
Content:
```
{cf['content']}
```

The output MUST be a JSON object with 'path' and 'content' (the markdown spec with YAML frontmatter).
For example:
{{
  "path": "behaviors/{base_id}.spec.md",
  "content": "---\\nid: behaviors/{base_id}\\nversion: 1.0.0\\nstatus: approved\\nparent: behaviors\\ndepends_on:\\n  - behaviors/other_file\\n---\\n\\n# Spec content here..."
}}

Rules:
1. ONLY output the raw JSON object. Do not wrap it in markdown.
2. Use the Project File List to infer what valid dependencies exist (prefix them with behaviors/). If this file imports or relies on logic from another file in the project, list it in depends_on.
"""
        try:
            resp = client.models.generate_content(
                model=config.model,
                contents=prompt,
            )
            data = extract_json(resp.text)
            
            # extract_json handles both JSON objects and arrays depending on the LLM's hallucination
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            out_path = specs_dir / data["path"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(data["content"], "utf-8")
        except Exception as e:
            click.echo(f"    Failed to process {cf['path']}: {e}\n{resp.text if 'resp' in locals() else ''}")

    click.echo("File-by-file extraction complete!")
