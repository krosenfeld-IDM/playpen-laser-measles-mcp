# README
Repository for playing with laser-measles MCP

## Getting Started

This repository includes the following git submodules in `src/`. Since these repositories are private, SSH access is required.

- [laser-measles](https://github.com/InstituteforDiseaseModeling/laser-measles) — `src/laser-measles`
- [laser-mcp](https://github.com/InstituteforDiseaseModeling/laser-mcp) — `src/laser-mcp`

### Cloning with submodules

```bash
git clone --recurse-submodules git@github.com:<owner>/playpen-laser-measles-mcp.git
```

### Initializing submodules after cloning

If you already cloned without `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

### Updating the submodule to the latest commit

```bash
git submodule update --remote src/laser-measles
git submodule update --remote src/laser-mcp
```

## Links
- [laser-mcp](https://github.com/InstituteforDiseaseModeling/laser-mcp/blob/main/README.md)
- [laser-measles-wiki](https://github.com/InstituteforDiseaseModeling/laser-measles/wiki)