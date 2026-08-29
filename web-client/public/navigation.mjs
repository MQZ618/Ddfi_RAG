export function navigateToSection(item, root = document) {
  const targetId = item?.dataset?.target;
  const target = targetId ? root.getElementById(targetId) : null;
  if (!target) return false;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  return true;
}

export function activateNavigationItem(item, items) {
  for (const other of items) {
    const active = other === item;
    other.classList.toggle("active", active);
    if (active) other.setAttribute("aria-current", "page");
    else other.removeAttribute("aria-current");
  }
}
