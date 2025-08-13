
"""
Python Data Types Mini‑Trainer (CLI)
-----------------------------------
Запускай в терминале:  python trainer.py

Особенности:
- 20+ заданий по встроенным типам (immutable/mutable)
- Два уровня сложности (разогрев / сложнее)
- Мгновенная проверка, подсказки и пояснения
- Безопасная проверка выражений через AST

Советы:
- Отвечай коротко: числом, строкой, выражением Python или вариантом ответа (A/B/C/D)
- Для задач-выражений пиши только выражение, без 'print' и лишних точек с запятой
"""

from __future__ import annotations
import ast
import textwrap
import random
from dataclasses import dataclass
from typing import Callable, Any, Optional, Dict, List, Tuple

# ---------------------- Безопасное вычисление выражений ----------------------

ALLOWED_BUILTINS = {
    'None': None,
    'True': True,
    'False': False,
    'len': len,
    'sum': sum,
    'min': min,
    'max': max,
    'sorted': sorted,
    'range': range,
    'set': set,
    'dict': dict,
    'list': list,
    'tuple': tuple,
    'bytes': bytes,
    'bytearray': bytearray,
}

ALLOWED_NODES = (
    ast.Module, ast.Expr,
    ast.Load, ast.Store, ast.Del,
    ast.Name, ast.Constant,
    ast.Tuple, ast.List, ast.Set, ast.Dict,
    ast.UnaryOp, ast.UAdd, ast.USub, ast.Not, ast.Invert,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.MatMult, ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift,
    ast.BoolOp, ast.And, ast.Or,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.Call, ast.keyword,
    ast.Slice, ast.ExtSlice, ast.Index,
    ast.Subscript,
    ast.JoinedStr, ast.FormattedValue,
)

ALLOWED_NAMES = set(ALLOWED_BUILTINS.keys()) | {
    # Переменные окружения задач подставляются динамически
    'x', 's', 'a', 'b', 't', 'd', 'nums', 's1', 's2', 'r', 'ba', 'fs'
}

ALLOWED_CALLS = {
    'len', 'sum', 'min', 'max', 'sorted', 'range', 'set', 'dict', 'list', 'tuple', 'bytes', 'bytearray'
}


def _validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Недопустимый синтаксический элемент: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in ALLOWED_CALLS:
                    raise ValueError(f"Недопустимый вызов: {node.func.id}()")
            else:
                raise ValueError("Разрешены только простые вызовы встроенных функций")
        if isinstance(node, ast.Name):
            if node.id not in ALLOWED_NAMES:
                raise ValueError(f"Недопустимое имя: {node.id}")


def safe_eval(expr: str, env: Optional[Dict[str, Any]] = None) -> Any:
    """Оценивает выражение Python безопасно с помощью AST."""
    expr = expr.strip()
    if not expr:
        raise ValueError("Пустое выражение")
    tree = ast.parse(expr, mode='eval')
    _validate_ast(tree)
    globals_env = {**ALLOWED_BUILTINS}
    locals_env = {}
    if env:
        # Разрешаем переданные переменные окружения (например, x=None)
        for k, v in env.items():
            if k not in ALLOWED_NAMES:
                raise ValueError(f"Недопустимое имя переменной окружения: {k}")
        globals_env.update(env)
    return eval(compile(tree, filename='<expr>', mode='eval'), globals_env, locals_env)


# ----------------------------- Описание задач -----------------------------

Checker = Callable[[str], Tuple[bool, str]]

@dataclass
class Task:
    id: str
    title: str
    level: str  # 'easy' | 'hard'
    prompt: str
    hint: str
    checker: Checker


# Вспомогательные фабрики проверок

def check_exact(expected: str) -> Checker:
    exp = expected.strip()
    def inner(ans: str) -> Tuple[bool, str]:
        ok = ans.strip() == exp
        return ok, ("Верно!" if ok else f"Ожидалось: {exp}")
    return inner


def check_mc(correct: str) -> Checker:
    correct = correct.strip().upper()
    def inner(ans: str) -> Tuple[bool, str]:
        a = ans.strip().upper()
        ok = a == correct
        return ok, ("Верно!" if ok else f"Неверно. Правильный ответ: {correct}")
    return inner


def check_eval_equals(env: Dict[str, Any], expected: Any) -> Checker:
    def inner(ans: str) -> Tuple[bool, str]:
        try:
            val = safe_eval(ans, env)
        except Exception as e:
            return False, f"Ошибка разбора/вычисления: {e}"
        ok = val == expected
        expl = f"Получилось {val!r}, ожидалось {expected!r}"
        return ok, ("Верно! " + expl if ok else "Неверно. " + expl)
    return inner


def check_eval_predicate(env: Dict[str, Any], predicate: Callable[[Any], bool], expected_str: str) -> Checker:
    def inner(ans: str) -> Tuple[bool, str]:
        try:
            val = safe_eval(ans, env)
        except Exception as e:
            return False, f"Ошибка: {e}"
        ok = predicate(val)
        return ok, ("Верно!" if ok else f"Неверно. Ожидалось: {expected_str}")
    return inner


def check_textio(expected_lines: List[str]) -> Checker:
    exp = [l.strip() for l in expected_lines]
    def inner(ans: str) -> Tuple[bool, str]:
        got = [x.strip() for x in ans.strip().split(';') if x.strip()]
        ok = got == exp
        return ok, ("Верно!" if ok else f"Ожидалось: {'; '.join(exp)}")
    return inner


# Сборка задач

tasks: List[Task] = [
    # NoneType
    Task(
        id="none_is",
        title="Проверка на None",
        level="easy",
        prompt=textwrap.dedent(
            """
            Дано: x = None
            Напиши выражение, которое True, только если x действительно None.
            (Пиши ТОЛЬКО выражение.)
            """
        ).strip(),
        hint="Используй оператор идентичности, не сравнение.",
        checker=check_eval_equals({'x': None}, True),
    ),
    Task(
        id="none_default",
        title="Функция с безопасным значением по умолчанию",
        level="hard",
        prompt=textwrap.dedent(
            """
            Что выведет программа? Ответ запиши как два вывода через ';'
            (пример: [1]; [1])

            def f(a=None):
                if a is None:
                    a = []
                a.append(1)
                return a

            print(f())
            print(f())
            """
        ).strip(),
        hint="При a=None новая пустая list создаётся на каждом вызове.",
        checker=check_textio(["[1]", "[1]"]),
    ),

    # bool
    Task(
        id="bool_truth",
        title="Истинность",
        level="easy",
        prompt="Что выведет print? Запиши через ';' без пробелов: bool(\"\"); bool([0])",
        hint="Пустая строка — ложь, непустой список — истина.",
        checker=check_textio(["False", "True"]),
    ),
    Task(
        id="bool_spaces",
        title="Непустая непусто-пробельная строка",
        level="hard",
        prompt="Напиши выражение, которое True только если s — непустая строка, не состоящая лишь из пробелов. Дано: s='  hi  '",
        hint="Комбинируй strip() и проверку истинности.",
        checker=check_eval_equals({'s': '  hi  '}, True),
    ),

    # int/float
    Task(
        id="float_peculiar",
        title="Плавающая точка",
        level="easy",
        prompt="Что выведет выражение: 0.1 + 0.2 == 0.3 ? (Ответ: True или False)",
        hint="IEEE 754 даёт накопление ошибки.",
        checker=check_exact("False"),
    ),
    Task(
        id="sum_gauss",
        title="Сумма 1..1_000_000",
        level="hard",
        prompt="Напиши выражение без циклов, считающее сумму чисел от 1 до 1_000_000 включительно.",
        hint="Вспомни формулу Гаусса n*(n+1)//2.",
        checker=check_eval_equals({}, 1_000_000 * 1_000_001 // 2),
    ),

    # str
    Task(
        id="str_strip_title",
        title="Обрезка и капитализация",
        level="easy",
        prompt="Дано: s='  python  '. Напиши выражение, возвращающее 'Python'.",
        hint="Комбинация strip() + capitalize().",
        checker=check_eval_equals({'s': '  python  '}, 'Python'),
    ),
    Task(
        id="str_vowels",
        title="Подсчёт гласных",
        level="hard",
        prompt="Дано: s='Привет, Python!'. Напиши выражение, которое возвращает количество гласных (русские и английские).",
        hint="Используй set гласных и sum(ch in vowels for ch in s.lower()).",
        checker=check_eval_equals({'s': 'Привет, Python!'}, 4),
    ),

    # tuple
    Task(
        id="tuple_one",
        title="Кортеж из одного элемента",
        level="easy",
        prompt="Создай кортеж из одного элемента со значением 5 (напиши выражение).",
        hint="Одна запятая обязательна.",
        checker=check_eval_predicate({}, lambda v: isinstance(v, tuple) and v == (5,), "(5,)"),
    ),
    Task(
        id="tuple_mutable_inside",
        title="Неизменяемость контейнера и изменяемость элемента",
        level="hard",
        prompt=textwrap.dedent(
            """
            Что напечатает код? Ответ как кортеж.
            t = (1, 2, [3, 4])
            t[2].append(5)
            print(t)
            """
        ).strip(),
        hint="Кортеж неизменяем, но список внутри — изменяем.",
        checker=check_exact("(1, 2, [3, 4, 5])"),
    ),

    # list
    Task(
        id="list_copy",
        title="Копия списка",
        level="easy",
        prompt="Дано: a=[1,2,3]. Напиши выражение, создающее поверхностную копию списка.",
        hint="Варианты: a.copy() или a[:].",
        checker=check_eval_predicate({'a': [1,2,3]}, lambda v: isinstance(v, list) and v == [1,2,3] and v is not None, "список-копия"),
    ),
    Task(
        id="list_remove_evens",
        title="Удаление чётных на месте",
        level="hard",
        prompt=textwrap.dedent(
            """
            Дано: nums = [1,2,3,4,5,6]
            Напиши выражение/код ОДНОЙ СТРОКОЙ, которое удалит все чётные числа ИЗ nums на месте (in-place).
            Подсказка: срезовая запись.
            """
        ).strip(),
        hint="nums[:] = [x for x in nums if x % 2]",
        checker=lambda ans: (
            (lambda: (
                (lambda res: (
                    isinstance(res, list) and res == [1,3,5]
                ))(
                    (lambda: (
                        (lambda _nums: (
                            exec(ans, {}, {'nums': _nums}) or _nums
                        ))([1,2,3,4,5,6])
                    ))()
                )
            ))(),
            "Верно!" if (lambda: (
                (lambda res: (
                    isinstance(res, list) and res == [1,3,5]
                ))(
                    (lambda: (
                        (lambda _nums: (
                            exec(ans, {}, {'nums': _nums}) or _nums
                        ))([1,2,3,4,5,6])
                    ))()
                )
            ))() else "Неверно. Ожидалось, что nums станет [1,3,5]"
        ),
    ),

    # dict
    Task(
        id="dict_get_default",
        title="get с запасным значением",
        level="easy",
        prompt="Дано: d={'a':1,'b':2}. Выражение, которое вернёт значение по ключу 'x' или 0, если ключа нет.",
        hint="d.get('x', 0)",
        checker=check_eval_equals({'d': {'a':1,'b':2}}, 0),
    ),
    Task(
        id="dict_comp",
        title="Словарное включение",
        level="hard",
        prompt="Построй выражение-словарь: ключ — число, значение — его квадрат, для чисел 1..5.",
        hint="{i: i*i for i in range(1,6)}",
        checker=check_eval_equals({}, {i: i*i for i in range(1,6)}),
    ),

    # set
    Task(
        id="set_dedup",
        title="Удаление дубликатов",
        level="easy",
        prompt="Дано: nums=[1,2,2,3,3,3,4]. Напиши выражение, возвращающее список уникальных чисел (порядок не важен).",
        hint="list(set(nums))",
        checker=check_eval_predicate({'nums': [1,2,2,3,3,3,4]}, lambda v: isinstance(v, list) and set(v) == {1,2,3,4}, "список уникальных значений"),
    ),
    Task(
        id="set_intersection",
        title="Пересечение множеств",
        level="hard",
        prompt="Дано: s1={1,2,3}, s2={2,3,4}. Выражение, возвращающее элементы, которые есть в обоих множествах.",
        hint="s1 & s2",
        checker=check_eval_equals({'s1': {1,2,3}, 's2': {2,3,4}}, {2,3}),
    ),

    # bytes / bytearray
    Task(
        id="bytes_from_str",
        title="bytes из строки",
        level="easy",
        prompt="Напиши выражение, создающее bytes из строки 'abc' в UTF-8.",
        hint="'abc'.encode('utf-8') или bytes('abc','utf-8')",
        checker=check_eval_equals({}, 'abc'.encode('utf-8')),
    ),
    Task(
        id="bytearray_modify",
        title="Правка первого байта",
        level="hard",
        prompt=textwrap.dedent(
            """
            Дано: ba = bytearray(b'abc')
            Напиши выражение одной строкой, которое заменит первый байт на код 'A'.
            После выполнения ba должно стать bytearray(b'Abc').
            """
        ).strip(),
        hint="ba[0] = ord('A')",
        checker=lambda ans: (
            (lambda: (
                (lambda res: res == bytearray(b'Abc'))(
                    (lambda: (
                        (lambda _ba: (
                            exec(ans, {}, {'ba': _ba}) or _ba
                        ))(bytearray(b'abc'))
                    ))()
                )
            ))(),
            "Верно!" if (lambda: (
                (lambda res: res == bytearray(b'Abc'))(
                    (lambda: (
                        (lambda _ba: (
                            exec(ans, {}, {'ba': _ba}) or _ba
                        ))(bytearray(b'abc'))
                    ))()
                )
            ))() else "Неверно. Ожидалось bytearray(b'Abc')"
        ),
    ),

    # range
    Task(
        id="range_desc",
        title="Обратный range",
        level="easy",
        prompt="Выражение: range от 10 до 0 с шагом -2 (включая 10, исключая 0).",
        hint="range(10, 0, -2)",
        checker=check_eval_equals({}, range(10, 0, -2)),
    ),
    Task(
        id="range_zero",
        title="Пустой range",
        level="hard",
        prompt="Что вернёт list(range(0))? Напиши точный вывод.",
        hint="Пустой список.",
        checker=check_exact("[]"),
    ),
]

# ----------------------------- Движок тренажёра -----------------------------

WELCOME = """
Добро пожаловать в мини‑тренажёр по типам данных Python!
Выбери режим:
  1) Разогрев (базовые)
  2) Чуть сложнее
  3) Смешанный (всё вперемешку)
Напечатай 1/2/3 и жми Enter.
""".strip()


def select_mode() -> str:
    print(WELCOME)
    while True:
        choice = input("> ").strip()
        if choice in {"1", "2", "3"}:
            return {"1": "easy", "2": "hard", "3": "mixed"}[choice]
        print("Введите 1, 2 или 3.")


def run_tasks(mode: str) -> None:
    if mode == "mixed":
        pool = tasks[:]
    else:
        pool = [t for t in tasks if t.level == mode]

    random.shuffle(pool)
    score = 0
    total = len(pool)

    print(f"\nСтартуем! Всего задач: {total}. Для подсказки введи: ?  Для выхода: q\n")

    for i, task in enumerate(pool, 1):
        print(f"[{i}/{total}] {task.title}")
        print(textwrap.indent(task.prompt, prefix="  "))

        while True:
            ans = input("Ваш ответ: ").rstrip("\n")
            if ans.strip().lower() == 'q':
                print("Выход из тренажёра. Спасибо за игру!")
                print(f"Результат: {score}/{i-1}")
                return
            if ans.strip() == '?':
                print(f"Подсказка: {task.hint}")
                continue
            try:
                ok, msg = task.checker(ans)
            except Exception as e:
                ok, msg = False, f"Ошибка проверки: {e}"
            print(msg)
            if ok:
                score += 1
                break
            else:
                # Даем возможность ещё раз попробовать
                retry = input("Попробовать ещё раз? (y/n): ").strip().lower()
                if retry != 'y':
                    break
        print("-" * 60)

    print(f"Готово! Ваш счёт: {score}/{total}")
    if score == total:
        print("Идеально! 🔥")
    elif score / total >= 0.7:
        print("Отличный результат! 💪")
    else:
        print("Хорошее начало — можно ещё потренироваться. 🙂")


if __name__ == "__main__":
    mode = select_mode()
    run_tasks(mode)

