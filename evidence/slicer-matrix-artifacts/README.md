# Measurement artifacts only

These compressed toolpaths omit normal printer startup, support, adhesion and purge operations. Do not send them to a printer.

The authoritative [matrix record](../slicer-matrix.json) records 30 attempted cases, 27 completed deposition measurements and three slicer rejections. It includes compressed and uncompressed SHA-256 hashes. The [method and table](../../docs/SLICER-MATRIX.md) explain the scope and limitations.

Each completed case retains its exact oriented STL, G-code, effective settings, raw placement XML and diagnostic logs. Rejected cases retain only files actually produced. A `*.log.gz` containing no text is the captured stdout/stderr of a successful command; detailed logging is in `*.diagnostic.log.gz`.
