"use client";

const KEY = "omniscan.compare";

export function compareIds(): string[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function addToCompare(id: string) {
  const ids = [id, ...compareIds().filter((x) => x !== id)].slice(0, 6);
  try {
    localStorage.setItem(KEY, JSON.stringify(ids));
  } catch {
    /* ignore */
  }
}

export function removeFromCompare(id: string) {
  try {
    localStorage.setItem(KEY, JSON.stringify(compareIds().filter((x) => x !== id)));
  } catch {
    /* ignore */
  }
}
