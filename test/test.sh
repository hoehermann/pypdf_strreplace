cd "$(dirname "$0")"/..

do_test() {
    echo "Test $@…"
    tmpdir="$(mktemp -d)"
    python3 pypdf_strreplace.py --output "$tmpdir"/"$1".pdf --input pdfs/"$2".pdf --search "$3" --replace "$4"
    test -f "$tmpdir"/"$1".pdf || return
    convert -density 150 "$tmpdir"/"$1".pdf "$tmpdir"/"$1".tiff # -compress LZW
    echo -n "Difference: "
    compare test/"$1".tiff "$tmpdir"/"$1".tiff -metric AE "$tmpdir"/compare-result.pgm
    echo ""
    rm -r "$tmpdir"
}

# simple tests (affect only one operand in one operation)
do_test "inkscape_simple" "Inkscape" "Inkscape 1.1.2"  "pleasure"
do_test "libreoffice_simple" "LibreOffice" "7.3.2" "infinite"
do_test "dmytryo_simple" "Dmytro" "PDF" "DOC"
do_test "xelatex_simple" "xelatex" "symbol" "character"

# less simple test (affect one operation, but multiple operands)
do_test "inkscape_multiple_operands" "Inkscape" "created" "made"

# even less simple test (affect multiple operations)
do_test "xelatex_multiple_operations" "xelatex" "n α symbo" "ny content meaningfu"

# replace multiple occurrences
do_test "dmytryo_multiple_occurrences" "Dmytro" "text" "fuzz"

# this shows how horizontal positioning can be off
# python3 pypdf_strreplace.py --input pdfs/xelatex.pdf --search "mes wit" --replace "ws can was" --output out.pdf

# the replacement may contain the needle
# test for infinite loops
timeout --verbose 1 python3 pypdf_strreplace.py --input pdfs/Dmytro.pdf --search text --replace context --output out.pdf 
timeout --verbose 1 python3 pypdf_strreplace.py --input pdfs/Dmytro.pdf --search text --replace text --output out.pdf 
timeout --verbose 1 python3 pypdf_strreplace.py --input pdfs/Dmytro.pdf --search text --replace contextual --output out.pdf 

