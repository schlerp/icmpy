# CLI tips

## Use `next` to keep moving

Once a workspace has stages, you rarely need to remember stage numbers:

```bash
icmp stage run next
```

This runs the first stage whose `output/` directory is empty or missing.

## Dry-run before you commit

Most commands support `--dry-run`:

```bash
icmp init my-workspace --dry-run
icmp build --template api-design --dry-run
```

## Non-interactive builds

Create an `answers.json` file:

```json
{
  "workspace_name": "my-api",
  "api_name": "Orders API",
  "consumer": "frontend checkout",
  "base_url": "/api/v2",
  "auth_method": "OAuth2"
}
```

Then build without prompts:

```bash
icmp build --template api-design --answers-file answers.json
```

## Watch token counts

`icmp stage run` estimates the token count of the assembled bundle. If it exceeds 8,000 tokens, consider:

- Splitting the stage into smaller stages
- Moving reference material out of the stage contract
- Asking the previous stage to produce a more condensed output

## Shell completion

Generate completion for your shell:

```bash
icmp completion bash > /tmp/icmp-completion.bash
source /tmp/icmp-completion.bash
```

## Validate in CI

Add `icmp validate` to a CI step to catch broken workspace structure before deployment:

```yaml
- run: |
    pip install icmpy
    icmp validate --workspace ./my-workspace
```

## Dispatch to an LLM harness

Run a stage directly through a supported harness instead of copy-pasting the bundle:

```bash
icmp stage run next --harness claude
icmp stage run 03 --harness pi
```

Use `--dry-run` to preview the command, and `icmp harness list` to see supported adapters.
