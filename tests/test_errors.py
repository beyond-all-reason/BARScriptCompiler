import pytest

from conftest import run_compiler


@pytest.mark.parametrize(
	("name", "content", "expected"),
	[
		(
			"unclosed_block",
			"piece base;\n"
			"Create()\n"
			"{\n"
			"\tmove base to x-axis [1] speed [1];\n"
			"\tif ( TRUE ) {\n"
			"}\n",
			"Syntax Error!",
		),
		(
			"unknown_statement",
			"piece base;\n"
			"Create()\n"
			"{\n"
			"\tbogus-statement-xyz;\n"
			"}\n",
			"Syntax Error!",
		),
		(
			"missing_include",
			'#include "no_such_header_xyz.h"\n'
			"piece base;\n"
			"Create()\n"
			"{\n"
			"}\n",
			"Preprocessor error",
		),
	],
)
def test_invalid_input_fails(tmp_path, name, content, expected):
	bos = tmp_path / (name + ".bos")
	bos.write_text(content)
	result = run_compiler(bos)
	assert result.returncode != 0
	assert expected in result.stdout + result.stderr
	assert not bos.with_suffix(".cob").exists()
