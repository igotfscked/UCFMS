#!/usr/bin/awk -f
#
# ucfnorm.awk - normalize Texas UCF (unclaimed property) data files.
#
# Input: the fixed-width 469-byte, 27-field record in LAYOUT.md
# (Jake's revised map, 2026-10-14). One record per line; LF or CRLF.
#
# Usage:
#   LC_ALL=C awk -f ucfnorm.awk [-v name=value ...] file ... > out
#
# Variables (all optional):
#   fmt=csv      Output format: csv (default), pipe, tsv, or fixed.
#                fixed writes clean 469-byte records in the original
#                layout (fields trimmed and re-padded, numbers zero-filled,
#                dates kept MM/DD/YYYY, no CR), ready for UCFLOAD.
#   header=1     Write a header row of field names (delimited formats).
#   dates=iso    Date output: iso (YYYY-MM-DD, default) or mdy (MM/DD/YYYY).
#   dollars=dec  DollarAmount: dec (62.70, default) or raw (0000006270).
#   zip=dash     ZIP codes: dash (78401 or 78401-1234, default; a +4 of
#                0000 is dropped) or raw (as on the file).
#   squeeze=1    Collapse runs of inner blanks in text fields to one.
#   propid=0     1 adds a PropertyID column (bytes 202-227) at the end.
#   strict=0     1 drops records that fail a check instead of keeping them.
#   stream=0     1 for a file with no line breaks (a binary download from
#                the mainframe): each line is cut into 469-byte records.
#
# Checks: record length, NRFlag Y/N, DollarAmount and NumberOfShares all
# digits, dates MM/DD/YYYY or blank. Each problem is reported on stderr
# with the file name and line number; a summary is printed at the end.
# In non-strict mode short records are padded and long ones truncated.
#
# Run under LC_ALL=C so length() and substr() count bytes, not
# characters. Works with POSIX awk, mawk, gawk, and busybox awk.

BEGIN {
    RECLEN = 469
    if (fmt == "")      fmt = "csv"
    if (header == "")   header = 1
    if (dates == "")    dates = "iso"
    if (dollars == "")  dollars = "dec"
    if (zip == "")      zip = "dash"
    if (squeeze == "")  squeeze = 1
    if (propid == "")   propid = 0
    if (strict == "")   strict = 0
    if (stream == "")   stream = 0

    if      (fmt == "csv")   OUTSEP = ","
    else if (fmt == "pipe")  OUTSEP = "|"
    else if (fmt == "tsv")   OUTSEP = "\t"
    else if (fmt == "fixed") OUTSEP = ""
    else { print "ucfnorm: fmt must be csv, pipe, tsv or fixed" > "/dev/stderr"; bad_args = 1; exit 2 }
    if (dates != "iso" && dates != "mdy") { print "ucfnorm: dates must be iso or mdy" > "/dev/stderr"; bad_args = 1; exit 2 }
    if (dollars != "dec" && dollars != "raw") { print "ucfnorm: dollars must be dec or raw" > "/dev/stderr"; bad_args = 1; exit 2 }
    if (zip != "dash" && zip != "raw") { print "ucfnorm: zip must be dash or raw" > "/dev/stderr"; bad_args = 1; exit 2 }

    # name:length:type   type: t=text, n=zero-filled number, d=date,
    # z=ZIP, $=implied-cents dollars, f=flag
    split("OwnerLastName:40:t OwnerFirstName:30:t OwnerAddressLine1:30:t " \
          "OwnerAddressLine2:30:t OwnerAddressLine3:30:t OwnerCity:30:t " \
          "OwnerState:2:t OwnerZipCode:9:z HolderIDNumber:12:t " \
          "HolderReportYear:4:t PropertyTypeCode:4:t SequenceNumber:6:t " \
          "NRFlag:1:f BeginningTransactionDate:10:d EndingTransactionDate:10:d " \
          "DollarAmount:10:$ NumberOfShares:10:n ReportDate:10:d " \
          "HolderName:40:t HolderAddressLine1:30:t HolderAddressLine2:30:t " \
          "HolderAddressLine3:30:t HolderCity:30:t HolderState:2:t " \
          "HolderZipCode:9:z UpdatedDate:10:d LastUpdatedDate:10:d", spec, " ")
    NF_UCF = 0
    pos = 1
    for (i = 1; spec[i] != ""; i++) {
        split(spec[i], p, ":")
        NF_UCF++
        fname[i] = p[1]; flen[i] = p[2] + 0; ftype[i] = p[3]; fstart[i] = pos
        pos += flen[i]
    }
    if (pos - 1 != RECLEN) { print "ucfnorm: layout adds up to " (pos - 1) " bytes, not " RECLEN > "/dev/stderr"; bad_args = 1; exit 2 }

    BLANKS = sprintf("%" RECLEN "s", "")
    nread = nout = nwarn = ndrop = 0

    if (header + 0 && fmt != "fixed") {
        line = ""
        for (i = 1; i <= NF_UCF; i++) line = line (i > 1 ? OUTSEP : "") fname[i]
        if (propid + 0) line = line OUTSEP "PropertyID"
        print line
    }
}

function warn(msg) {
    printf("ucfnorm: %s:%d: %s\n", FILENAME, FNR, msg) > "/dev/stderr"
    nwarn++
    rec_bad = 1
}

function trim(s) {
    sub(/^[ \t]+/, "", s)
    sub(/[ \t]+$/, "", s)
    if (squeeze + 0) gsub(/[ \t][ \t]+/, " ", s)
    return s
}

function is_digits(s) { return s ~ /^[0-9]+$/ }

# Strip leading zeros from an all-digit string; "" stays "".
function unzero(s) {
    sub(/^0+/, "", s)
    return (s == "") ? "0" : s
}

function norm_date(s, name,    m, d, y) {
    if (s == "") return ""
    if (s !~ /^[0-9][0-9]\/[0-9][0-9]\/[0-9][0-9][0-9][0-9]$/) {
        warn(name " is not MM/DD/YYYY: \"" s "\"")
        return s
    }
    m = substr(s, 1, 2) + 0; d = substr(s, 4, 2) + 0; y = substr(s, 7, 4)
    if (m < 1 || m > 12 || d < 1 || d > 31) warn(name " is not a valid date: \"" s "\"")
    if (fmt == "fixed" || dates == "mdy") return s
    return y "-" substr(s, 1, 2) "-" substr(s, 4, 2)
}

function norm_zip(s, name) {
    if (s == "") return ""
    if (s !~ /^[0-9]+$/ || (length(s) != 5 && length(s) != 9))
        warn(name " is not a 5- or 9-digit ZIP: \"" s "\"")
    if (fmt == "fixed" || zip == "raw" || length(s) != 9) return s
    if (substr(s, 6, 4) == "0000") return substr(s, 1, 5)
    return substr(s, 1, 5) "-" substr(s, 6, 4)
}

function norm_dollars(s, name,    c) {
    if (s == "") return (fmt == "fixed") ? "0000000000" : ""
    if (!is_digits(s)) { warn(name " is not all digits: \"" s "\""); return s }
    if (fmt == "fixed") return zfill(s, 10)
    if (dollars == "raw") return s
    c = unzero(s)
    while (length(c) < 3) c = "0" c
    return substr(c, 1, length(c) - 2) "." substr(c, length(c) - 1)
}

function norm_number(s, name) {
    if (s == "") return (fmt == "fixed") ? "0000000000" : ""
    if (!is_digits(s)) { warn(name " is not all digits: \"" s "\""); return s }
    return (fmt == "fixed") ? zfill(s, 10) : unzero(s)
}

# Quote or clean a value for the delimited output formats.
function emit(s) {
    if (fmt == "csv") {
        if (s ~ /[",\n]/ || s ~ /^ | $/) { gsub(/"/, "\"\"", s); s = "\"" s "\"" }
        return s
    }
    gsub(OUTSEP == "|" ? "[|]" : "\t", " ", s)
    return s
}

# Left-pad an all-digit string with zeros to n bytes.
function zfill(s, n) {
    while (length(s) < n) s = "0" s
    return s
}

# Left-justify (text) or keep as is, then pad/truncate to the field width.
function fit(s, n) {
    if (length(s) > n) return substr(s, 1, n)
    return s substr(BLANKS, 1, n - length(s))
}

# Normalize one record and print it.
function do_record(rec,    len, raw, i, v, t, line) {
    nread++
    rec_bad = 0
    if (rec ~ /^[ \t]*$/) { warn("blank line skipped"); ndrop++; return }

    len = length(rec)
    if (len < RECLEN) {
        warn("record is " len " bytes, padded to " RECLEN)
        rec = rec substr(BLANKS, 1, RECLEN - len)
    } else if (len > RECLEN) {
        warn("record is " len " bytes, truncated to " RECLEN)
        rec = substr(rec, 1, RECLEN)
    }
    raw = rec

    for (i = 1; i <= NF_UCF; i++) {
        v = substr(raw, fstart[i], flen[i])
        t = ftype[i]
        if (t == "t") v = trim(v)
        else { gsub(/^[ \t]+|[ \t]+$/, "", v) }

        if      (t == "d") v = norm_date(v, fname[i])
        else if (t == "z") v = norm_zip(v, fname[i])
        else if (t == "$") v = norm_dollars(v, fname[i])
        else if (t == "n") v = norm_number(v, fname[i])
        else if (t == "f") {
            v = toupper(v)
            if (v != "Y" && v != "N") warn("NRFlag is not Y or N: \"" v "\"")
        }
        val[i] = v
    }

    if (rec_bad && strict + 0) { ndrop++; return }

    line = ""
    if (fmt == "fixed") {
        for (i = 1; i <= NF_UCF; i++) line = line fit(val[i], flen[i])
    } else {
        for (i = 1; i <= NF_UCF; i++) line = line (i > 1 ? OUTSEP : "") emit(val[i])
        if (propid + 0) line = line OUTSEP emit(substr(raw, 202, 26))
    }
    print line
    nout++
}

{
    sub(/\r$/, "")
    if (stream + 0) {
        # A binary transfer with no line breaks: cut into 469-byte records.
        for (off = 1; off <= length($0); off += RECLEN)
            do_record(substr($0, off, RECLEN))
    } else
        do_record($0)
}

END {
    if (bad_args) exit 2
    printf("ucfnorm: %d read, %d written, %d dropped, %d warnings\n",
           nread, nout, ndrop, nwarn) > "/dev/stderr"
}
