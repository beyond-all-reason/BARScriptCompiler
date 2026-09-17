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
		(
			"static_var_shadows_piece",
			"piece base;\n"
			"static-var base;\n"
			"Create()\n"
			"{\n"
			"}\n",
			"Piece names must be unique",
		),
		(
			"local_var_shadows_piece",
			"piece base;\n"
			"Create()\n"
			"{\n"
			"\tvar base;\n"
			"}\n",
			"Piece names must be unique",
		),
		(
			"func_arg_shadows_piece",
			"piece base;\n"
			"Create(base)\n"
			"{\n"
			"}\n",
			"Piece names must be unique",
		),
		(
			"piece_declared_after_shading_func",
			"Create(base)\n"
			"{\n"
			"}\n"
			"piece base;\n",
			"Piece names must be unique",
		),
		(
			"case_insensitive_piece_shadow",
			"piece base;\n"
			"Create(BASE)\n"
			"{\n"
			"}\n",
			"Piece names must be unique",
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
