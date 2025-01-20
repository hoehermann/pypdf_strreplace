cd "$(dirname "$0")"/..

if ! gm -version > /dev/null
then
    echo -e "\033[31;1mGraphicsMagick is not installed.\033[0m"
    exit 1
fi

do_test() {
    echo "Test $@…"
    tmpdir="$(mktemp -d "/tmp/test.$1.XXXXXXXXXX")"
    timeout --verbose 1 python3 pypdf_strreplace.py --output "$tmpdir"/output.pdf --input pdfs/"$2".pdf --search "$3" --replace "$4" > "$tmpdir"/messages.log
    gm convert -background white -extent 0x0 -density 150 +matte test/"$1".pdf "$tmpdir"/reference.tiff
    gm convert -background white -extent 0x0 -density 150 +matte "$tmpdir"/output.pdf "$tmpdir"/output.tiff
    pages_count=$(gm identify "$tmpdir"/output.tiff | wc -l)
    for i in $(seq 0 $(($pages_count - 1)))
    do 
        if gm compare "$tmpdir"/reference.tiff[$i] "$tmpdir"/output.tiff[$i] -metric PAE -maximum-error 0 > "$tmpdir"/messages.log
        then
            echo "Page $i OK"
        else
            echo -e "\033[31;1mTest failed!\033[0m"
        fi
    done
    rm -r "$tmpdir"
}

# simple tests (affect only one operand in one operation)
do_test "inkscape_simple" "Inkscape" "Inkscape 1.1.2" "pleasure"
do_test "libreoffice_simple" "LibreOffice" "7.3.2" "infinite"
do_test "dmytryo_simple" "Dmytro" "PDF" "DOC"
do_test "xelatex_simple" "xelatex" "symbol" "character"

# less simple test (affect one operation, but multiple operands)
do_test "inkscape_multiple_operands" "Inkscape" "created" "made"

# even less simple test (affect multiple operations)
do_test "xelatex_multiple_operations" "xelatex" "n α symbo" "ny content unti"
do_test "libreoffice_multiple_operations" "LibreOffice" "PDF file" "text document"

# replace multiple occurrences (but each affects only one operand in one operation)
do_test "dmytryo_multiple_occurrences" "Dmytro" "text" "fuzz"

# the replacement may contain the needle (test for infinite loop)
do_test "dmytryo_needle_remains" "Dmytro" "text" "context"

# this shows how horizontal positioning can be off
# python3 pypdf_strreplace.py --input pdfs/xelatex.pdf --search "mes wit" --replace "ws can was" --output out.pdf
