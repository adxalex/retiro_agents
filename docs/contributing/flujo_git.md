# Flujo Git y colaboración · Retiro RAG

## 1. Ramas

- `main`: versión estable; no se trabaja directamente sobre ella.
- `develop`: integración del equipo.
- Ramas secundarias: una por tarea, creadas desde `develop`.

Las PR se dirigen a `develop`. Al final, `develop` se fusiona en `main`.

## 2. Primera PR documental

El contrato debe estar en `develop` antes de crear las ramas técnicas:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c docs/shared-contract

git add docs/contracts/contrato_compartido_mvp_retiro.md
git add docs/architecture/pipeline_rag.md
git add docs/corpus/alcance_y_fuentes.md
git add docs/contributing/flujo_git.md
git add entregables/informe_decisiones.md
git add README.md

git commit -m "docs: add initial project documentation"
git push -u origin docs/shared-contract
```

La PR será `docs/shared-contract → develop`. Tras fusionarla:

```bash
git switch develop
git pull --ff-only origin develop
```

## 3. Ramas técnicas

```text
Alex       → feature/corpus-loaders
Alejandra  → feature/chunking-embeddings-index
David      → feature/retrieval-application
```

## 4. Circuito de revisión

- David revisa las PR de Alejandra.
- Alejandra revisa las PR de Alex.
- Alex revisa las PR de David.

```text
PR de Alejandra → revisa David
PR de Alex      → revisa Alejandra
PR de David     → revisa Alex
```

Si Alejandra abre la PR documental, David será el revisor responsable. Los demás también pueden comentar.

## 5. Lista de revisión

1. La PR tiene un alcance manejable.
2. Respeta el contrato.
3. No contiene secretos, `.env`, `.venv/` ni artefactos innecesarios.
4. Las pruebas relacionadas pasan.
5. No rompe otros bloques.
6. Configuración y documentación están actualizadas.
7. Los errores se gestionan con claridad.

La persona autora resuelve comentarios y conflictos antes del merge.

## 6. Flujo diario

```bash
git switch develop
git pull --ff-only origin develop
git switch feature/tu-rama
git merge develop
git status
git diff
```

Añadir únicamente los archivos de la tarea:

```bash
git add ruta/al/archivo.py
git diff --staged
git commit -m "feat: describe el cambio"
```

## 7. Commits

```text
docs: add shared RAG contract
feat: implement PDF loader
feat: add configurable chunking
feat: persist chunks in ChromaDB
test: verify idempotent reindexing
fix: preserve source metadata
```

Los commits deben ser pequeños, comprensibles y distribuidos durante el proyecto.

## 8. Seguridad

No se versionan:

```text
.env
.venv/
__pycache__/
chroma/
output/
```

Antes de hacer push:

```bash
git status
git diff --staged
```

## 9. Evidencia individual

Cada integrante debe aportar:

- Al menos una PR propia revisada y fusionada.
- Commits propios relacionados con su bloque.
- Una revisión sustancial de la persona asignada.
- Participación distribuida durante el proyecto.

## 10. Definición de terminado

Una PR puede fusionarse cuando cumple su objetivo, respeta el contrato, supera sus pruebas, no incluye secretos, contiene instrucciones de prueba, ha sido revisada y no tiene conflictos con `develop`.
