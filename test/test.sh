cd "$(dirname "$0")"/..

do_test() {
    echo "Test $@…"
    tmpdir="$(mktemp -d)"
    python3 pypdf_strreplace.py --output "$tmpdir"/"$1".pdf --input pdfs/"$2".pdf --search "$3" --replace "$4"
    test -f "$tmpdir"/"$1".pdf || return
    convert -density 150 -alpha off "$tmpdir"/"$1".pdf -compress LZW "$tmpdir"/"$1".tiff
    pages_count=$(identify "$tmpdir"/"$1".tiff | wc -l)
    total_difference=0
    for i in $(seq 0 $(($pages_count - 1)))
    do
        difference=$(compare -alpha off test/"$1".tiff[$i] "$tmpdir"/"$1".tiff[$i] -metric AE "$tmpdir"/compare-result_$i.pgm 2>&1)
        echo "Difference: $difference on page $i"
        total_difference=$(($total_difference + $difference))
    done
    if [[ $total_difference -gt 0 ]]
    then
        echo -e "\033[31;1mTest failed!\033[0m"
    else
        rm -r "$tmpdir"
    fi
}

# simple tests (affect only one operand in one operation)
do_test "inkscape_simple" "Inkscape" "Inkscape 1.1.2"  "pleasure"
do_test "libreoffice_simple" "LibreOffice" "7.3.2" "infinite"
do_test "dmytryo_simple" "Dmytro" "PDF" "DOC"
do_test "xelatex_simple" "xelatex" "symbol" "character"

# less simple test (affect one operation, but multiple operands)
do_test "inkscape_multiple_operands" "Inkscape" "created" "made"

# even less simple test (affect multiple operations)
do_test "xelatex_multiple_operations" "xelatex" "n α symbo" "ny content unti"

# replace multiple occurrences
do_test "dmytryo_multiple_occurrences" "Dmytro" "text" "fuzz"

# this shows how horizontal positioning can be off
# python3 pypdf_strreplace.py --input pdfs/xelatex.pdf --search "mes wit" --replace "ws can was" --output out.pdf

# the replacement may contain the needle
# test for infinite loops
timeout --verbose 1 python3 pypdf_strreplace.py --input pdfs/Dmytro.pdf --search text --replace context --output out.pdf 
timeout --verbose 1 python3 pypdf_strreplace.py --input pdfs/Dmytro.pdf --search text --replace text --output out.pdf 
timeout --verbose 1 python3 pypdf_strreplace.py --input pdfs/Dmytro.pdf --search text --replace contextual --output out.pdf 

