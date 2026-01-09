
export function titleCase(str) {
    if (!str) return "";
    return String(str)
        .toLowerCase()
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

export function sentenceCase(str) {
    if (!str) return "";
    const s = String(str);
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}
