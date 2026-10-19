# nextflow lint: callings-nf

3 errors, 5 warnings.

| Level | Count | Message |
|---|---:|---|
| Error | 2 | `index` is already declared |
| Warn | 2 | Variable was declared but not used |
| Warn | 2 | Implicit closure parameter is deprecated, declare an explicit parameter instead |
| Error | 1 | Statements cannot be mixed with script declarations -- move statements into a process, workflow, or function |
| Warn | 1 | The use of `Channel` to access channel factories is deprecated -- use `channel` instead |

| Level | Location | Message |
|---|---|---|
| Error | `examples/callings-nf/main.nf:41` | Statements cannot be mixed with script declarations -- move statements into a process, workflow, or function |
| Warn | `examples/callings-nf/main.nf:72` | The use of `Channel` to access channel factories is deprecated -- use `channel` instead |
| Error | `examples/callings-nf/modules.nf:161` | `index` is already declared |
| Error | `examples/callings-nf/modules.nf:191` | `index` is already declared |
| Warn | `examples/callings-nf/modules.nf:159` | Variable was declared but not used |
| Warn | `examples/callings-nf/modules.nf:189` | Variable was declared but not used |
| Warn | `examples/callings-nf/modules.nf:241` | Implicit closure parameter is deprecated, declare an explicit parameter instead |
| Warn | `examples/callings-nf/modules.nf:342` | Implicit closure parameter is deprecated, declare an explicit parameter instead |
