# Publication management operations

Stringprint keeps the interactive CLI while exposing the main publication workflow through an authenticated Django management interface. Long-running web actions are stored in the database and executed by one persistent worker.

## Running the local management environment

From the document-source repository, start the Stringprint shell as usual and run:

```text
startserver
```

This starts two independently supervised child processes:

- the Django preview server on `0.0.0.0:8000`;
- the publication operation worker.

Use `status` to see each process, PID, and log path. Use `stopserver`, `quit`, `exit`, or end-of-input to stop both. Server and worker logs are kept separately under `.stringprint/logs/`.

For production or diagnosis, the processes can be started independently:

```bash
python manage.py runserver 0.0.0.0:8000
python manage.py run_publication_operations
```

Use `--once` on the worker command to claim at most one queued operation and exit.

## Web access and permissions

The management interface is mounted at `/manage/` and requires a normal Django login. A user can only see and operate on the organisation assigned through their `UserSettings` membership. State-changing routes accept POST requests and retain Django CSRF protection.

The interface supports initial load, process, web/EPUB/Kindle render, archive, and explicitly enabled publishing. Publishing is disabled unless both conditions are met:

- the publication config contains `web_operations: [publish]`;
- a fixed `publish` configured command exists for the publication or organisation.

The browser never accepts arbitrary command names or shell input.

Web rendering generates plain HTML and EPUB independently; `skip_epub: true`
suppresses automatic EPUB output. MOBI is opt-in and requires an installed Kindle
generator configured through `KINDLEGEN_LOC` or available as `kindlegen` on PATH.
An explicit EPUB operation is still available for documents that skip automatic
EPUB generation. Optional download links reflect files produced by the build.

The original dashboard and browser-upload screens redirect to this interface.
Source files remain in the document repository; posted uploads to retired screens
do not create or modify publications. Legacy settings and header-image screens are read-only, with their organisation
access checks preserved. Edit repository YAML and source images, then reload.
Archive and publish requests expose optional hero/thumbnail regeneration; those
steps execute inside the same publication lock as archive creation and publishing.

## Operation states and recovery

Queued operations move through explicit states:

```text
pending -> running -> succeeded
                   -> failed
                   -> cancel_requested -> cancelled
                   -> interrupted
```

The worker records stages, heartbeats, a bounded error summary, a structured result, and a dedicated log file. The operation detail page shows recent log output without loading an unbounded file into the database or response.

Cancellation is immediate for pending work. Running work receives a cooperative cancellation request; an owned subprocess group is terminated gracefully and then forcibly after a bounded wait if necessary. Unrelated processes are never signalled.

A worker restart marks operations with expired heartbeats as `interrupted`. It does not resume them automatically because a filesystem mutation may be partially complete. Inspect the operation log and publication output, then use the explicit retry action. A retry creates a new pending record linked to the original history.

Only one fresh worker is allowed by default. Both queued and foreground CLI mutations acquire the same per-publication filesystem lock, so they fail clearly instead of writing the same source or output tree concurrently.

## Health and diagnosis

The publication and operation pages show whether a recent worker heartbeat is available. If the worker is unavailable, read-only pages remain usable and newly recorded work stays visibly pending.

For local failures:

1. Run `status` in the CLI and inspect the separate server and worker logs.
2. Confirm migrations are applied and start `run_publication_operations --once` to diagnose one queued item.
3. Inspect the operation detail, its stage, error summary, and recent log.
4. For an interrupted or failed mutation, verify generated files before creating an explicit retry.
5. Do not edit operation state directly; transition and retry services preserve the history and ownership rules.

The admin site exposes operation and worker records for diagnosis.

## Retention

Completed operation records and their owned logs can be pruned with:

```bash
python manage.py prune_publication_operations --days 90 --dry-run
python manage.py prune_publication_operations --days 90
```

Always run the dry run first. Log deletion is restricted to the configured operation-log root; paths outside it are not removed.

## CLI-only workflows

The following commands remain intentionally CLI-only because they are local authoring tools, interactive/batch conveniences, or unrestricted configured commands:

- `convertword`, `mergepdf`, `pdfpng`, `hero`, and `newdoc`;
- `loadall`, `loadunloaded`, and `publish_updated`;
- `preprocess`, arbitrary configured `command` values, and command-name fallback;
- organisation/document selection, listing, freshness inspection, and status commands.

Their publication filesystem mutations still use the shared foreground lock. Preprocessing used as part of the fixed `process` operation is available through the web interface. Arbitrary configured commands are deliberately not exposed through the browser.

## Concurrency policy

Worker concurrency remains one. The current workload is dominated by synchronous Django operations, filesystem writes, CPU work, and external tools, so async Django views would not add durability or safe ownership. The typed operation boundary can be adapted to a larger task system later if multiple hosts, scheduling, priorities, or higher throughput become requirements.
