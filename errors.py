from __future__ import annotations



def string_with_arrows(text, pos_start, pos_end):
	result = ''
	tab_width = 4

	# Calculate indices
	idx_start = text.rfind('\n', 0, pos_start.idx)
	if idx_start < 0:
		idx_start = 0
	else:
		idx_start += 1
	idx_end = text.find('\n', idx_start + 1)
	if idx_end < 0: idx_end = len(text)
	
	# Generate each line
	line_count = pos_end.ln - pos_start.ln + 1
	for i in range(line_count):
		# Calculate line columns
		line = text[idx_start:idx_end]
		col_start = pos_start.col if i == 0 else 0
		col_end = pos_end.col if i == line_count - 1 else len(line)

		# Append to result (with line numbers)
		line_no = pos_start.ln + i + 1
		gutter = f"{line_no} | "
		# expand tabs for correct caret alignment
		line = line.replace('\t', ' ' * tab_width)
		def expand_col(col, raw_line):
			extra = 0
			for ch in raw_line[:col]:
				if ch == '\t':
					extra += tab_width - 1
			return col + extra

		raw_line = text[idx_start:idx_end]
		col_start = expand_col(col_start, raw_line)
		col_end = expand_col(col_end, raw_line)
		result += gutter + line + '\n'
		if col_end <= col_start:
			col_end = col_start + 1
		caret_len = max(1, col_end - col_start)
		result += ' ' * (len(gutter) + col_start) + '^' * caret_len + '\n'

		# Re-calculate indices
		idx_start = idx_end
		idx_end = text.find('\n', idx_start + 1)
		if idx_end < 0: idx_end = len(text)

	return result.rstrip('\n')


def make_hint(error_name: str, details: str) -> str | None:
	details = details or ""
	if "Token cannot appear after previous tokens" in details:
		return "You may be missing a newline or a '}'."
	if "Expected" in details:
		expected = details.replace("Expected", "").strip()
		if expected:
			return f"Expected: {expected}. Check the syntax near the highlighted area."
		return "Check the syntax near the highlighted area."
	if "Illegal operation" in details:
		return "Check operand types and whether the operation is supported for them."
	if "Division by zero" in details or "Modulo by zero" in details:
		return "Make sure the divisor is not 0."
	if "Unclosed '{' in f-string" in details:
		return "Add a closing '}' in the f-string."
	if "Empty expression in f-string" in details:
		return "Put an expression between '{' and '}'."
	if "Can't find module" in details:
		return "Check the module name and the path in the .path file."
	if error_name == "Illegal Character":
		return "Remove the invalid character or escape it."
	return None


class Error:
    def __init__(self, pos_start, pos_end, error_name, details, hint: str | None = None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details
        self.hint = hint

    def set_pos(self, pos_start=None, pos_end=None):
        if pos_start is not None:
            self.pos_start = pos_start
        if pos_end is not None:
            self.pos_end = pos_end
        return self

    def __repr__(self) -> str:
        return f'{self.error_name}: {self.details}'

    def as_string(self):
        line = self.pos_start.ln + 1
        col = self.pos_start.col + 1
        result = f'{self.error_name}: {self.details}\n'
        result += f'File {self.pos_start.fn}, line {line}, column {col}'
        result += '\n\n' + string_with_arrows(
            self.pos_start.ftxt,
            self.pos_start,
            self.pos_end,
        )
        hint = self.hint or make_hint(self.error_name, self.details)
        if hint:
            result += f'\n\nHint: {hint}'
        return result

    def copy(self):
        try:
            return __class__(self.pos_start, self.pos_end, self.error_name, self.details, self.hint)
        except TypeError:
            return __class__(self.pos_start, self.pos_end, self.details)


class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Illegal Character', details)


class ExpectedCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, 'Expected Character', details)


class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details=''):
        super().__init__(pos_start, pos_end, 'Invalid Syntax', details or "Invalid syntax")


class RTError(Error):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, 'Runtime Error', details)
        self.context = context

    def set_context(self, context=None):
        return self

    def as_string(self):
        result = self.generate_traceback()
        line = self.pos_start.ln + 1
        col = self.pos_start.col + 1
        result += f'{self.error_name}: {self.details} (line {line}, column {col})\n'
        result += '\n\n' + string_with_arrows(
            self.pos_start.ftxt,
            self.pos_start,
            self.pos_end,
        )
        hint = self.hint or make_hint(self.error_name, self.details)
        if hint:
            result += f'\n\nHint: {hint}'
        return result

    def generate_traceback(self):
        result = ''
        pos = self.pos_start
        ctx = self.context

        while ctx:
            result = f'  File {pos.fn}, line {str(pos.ln + 1)}, in {ctx.display_name}\n' + result
            pos = ctx.parent_entry_pos
            ctx = ctx.parent

        return 'Traceback (most recent call last):\n' + result

    def copy(self):
        return __class__(self.pos_start, self.pos_end, self.details, self.context)


class TryError(RTError):
    def __init__(self, pos_start, pos_end, details, context, prev_error):
        super().__init__(pos_start, pos_end, details, context)
        self.prev_error = prev_error

    def generate_traceback(self):
        result = ""
        if self.prev_error:
            result += self.prev_error.as_string()
        result += "\nDuring the handling of the above error, another error occurred:\n\n"
        return result + super().generate_traceback()
