@AGENTS.md

## Notas para Claude Code
- Los comandos `/sdd-*` están en `.claude/commands/`; cada uno es una fase del flujo SDD descrito en `AGENTS.md`.
- No pases de fase sin aprobación explícita.
- Comentarios del código: breves, neutrales, sin nombres de personas ni referencias a herramientas de IA.
- Terminal de trabajo: PowerShell con `.venv` activo. Los scripts se ejecutan desde la raíz y como módulo: `python -m scripts.nombre`.