# WebI-Change-Source

## Introduction

This tool is used to bulk convert SAP Business Objects document queries from UNV to UNX.

## Project Structure

This project uses [uv](https://github.com/astral-sh/uv) to bootstrap the python virtual environment, to build the
package, and to run the tool

## Usage

This tool can be run completely without installation, requiring only `uv` to be installed:

```shell
uvx --python 3.14 --from git+https://github.com/Wits-Business-Intelligence-Services/WebI-Change-Source.git webi_change_source.exe
```
- `uvx` is `uv` special mode that creates temporary environments to install and run tools directly without installation.
- `--python 3.14` is needed as there is a chance your current shell's python version differs from what the tool expects.
- `--from <git url>` specifies that `uv` should pull this package from GitHub as this tool is not publised to PyPI
- `webi_change_source.exe` this package provides one tool and that is what we will be running. Everything below is
appended onto the above line

Running the tool the first time will generate a `settings.toml` file in the directory it is being run in. This file
will need to be populated with the settings required to access the CMS server, as well as the source and target universe
id's.

> NOTE: For ease of use

Create a PowerShell function so that you can simply use `webi-change-source` instead of the entire line above. This
will last until you close the terminal.

```shell
function webi-change-source {uvx --python 3.14 --from git+https://github.com/Wits-Business-Intelligence-Services/WebI-Change-Source.git webi_change_source.exe @args}
```

Now, you can call `webi-change-source <arguments>` instead.

## Commands

The tool is split into three commands:

```
 Usage: webi_change_source <COMMAND> [OPTIONS] {webi_document_list_path}

╭─ Commands ────────────────────────────────────────────────────────────────────╮
│ update-local-document-db                                                      │
│ perform-change-source                                                         │
│ full-pipeline                                                                 │
╰───────────────────────────────────────────────────────────────────────────────╯
╭─ Arguments ───────────────────────────────────────────────────────────────────╮
│ *    webi_document_list_path      <str>  Relative path to file with list of   │
│                                          WebI document IDs                    │
│                                          [required]                           │
╰───────────────────────────────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────────────────────────────╮
│ --num-workers        <int>  Run process in parallel up with up to 8 workers   │
│                             [default: 1]                                      │
│ --help                      Show this message and exit.                       │
╰───────────────────────────────────────────────────────────────────────────────╯
```

### update-local-document-db

This populates the local sqlite db `db.sqlite` with the details of the list of documents provided by
`webi_document_list_path`. This is useful for reporting and is used by the next step to decide on which actions to
take for each document and their respective queries.

### perform-change-source

This command will iterate through the provided `webi_document_list_path` and uses the local sqlite db data to decide 
whether to perform a change source operation on the document. This will use the `source_universe_id` and 
`target_universe_id` entries in `settings.toml` to choose what to do to each query. Only queries pointing to 
`source_universe_id` will be converted to `target_universe_id`.

The db table `conversions` contains the conversion results, with each run of `perform-change-source` creating a new 
`batch_id`. This allows the table to hold multiple conversion runs and still allow one to view the runs separately.

### full-pipeline

This runs the above two commands in order, retrieving the document and query details in the first step, then performing
the conversion on the appropriate documents from that list.