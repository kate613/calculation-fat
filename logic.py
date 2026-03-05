from database import get_product_by_name, search_product, get_user_norms


def find_product(name):
    return get_product_by_name(name) or search_product(name)


def calculate_nutrition(product, grams):
    if not product:
        return None
    product_id, product_name, cal, prot, fat, carbs = product
    m = grams / 100
    return {
        'product_id':   product_id,
        'product_name': product_name,
        'calories': round(cal  * m, 1),
        'protein':  round(prot * m, 1),
        'fat':      round(fat  * m, 1),
        'carbs':    round(carbs * m, 1),
    }


def format_daily_report(entries, totals, user_id):
    lines = ["Отчет за день:\n"]
    for name, grams, cal, *_ in entries:
        lines.append(f"{name}: {grams}г = {cal} kcal")

    cal, prot, fat, carbs = (v or 0 for v in totals)
    lines.append(f"\nВсего: {cal} kcal")
    lines.append(f"Б: {prot}г | Ж: {fat}г | У: {carbs}г")

    norms = get_user_norms(user_id)
    if norms[0] > 0:
        lines.append(f"\nНорма: Б {norms[0]}г | Ж {norms[1]}г | У {norms[2]}г")
        deficit = [
            f"Б не хватает {round(norms[0] - prot, 1)}г"  if prot  < norms[0] else None,
            f"Ж не хватает {round(norms[1] - fat,  1)}г"  if fat   < norms[1] else None,
            f"У не хватает {round(norms[2] - carbs, 1)}г" if carbs < norms[2] else None,
        ]
        deficit = [d for d in deficit if d]
        if deficit:
            lines.append(', '.join(deficit))
        else:
            lines.append("Норма достигнута")

    return '\n'.join(lines)


def format_weekly_report(entries, totals, user_id):
    lines = ["Отчет за неделю:"]
    current_date = None
    for name, grams, cal, *_, date in entries:
        if date != current_date:
            current_date = date
            lines.append(f"\n{date}")
        lines.append(f"{name}: {grams}г = {cal} kcal")

    cal, prot, fat, carbs = (v or 0 for v in totals)
    lines.append(f"\nВсего за неделю: {cal} kcal")
    lines.append(f"Б: {prot}г | Ж: {fat}г | У: {carbs}г")

    norms = get_user_norms(user_id)
    if norms[0] > 0:
        lines.append(
            f"\nСреднее в день: Б {prot/7:.0f}г | Ж {fat/7:.0f}г | У {carbs/7:.0f}г"
        )
        lines.append(f"Норма: Б {norms[0]}г | Ж {norms[1]}г | У {norms[2]}г")

    return '\n'.join(lines)
