"use client";

import React, { Children, isValidElement } from "react";

/**
 * Transforms a markdown <table> into a vertical card layout.
 *
 * Instead of rendering data in cramped columns, each table row becomes
 * a full-width card where column headers become inline labels and cell
 * content gets the full width to breathe.
 *
 * Example transformation:
 *   | Factor          | Risk Up         | Risk Down     |
 *   | Nature of work  | Long paragraph  | Long para...  |
 *
 * Becomes:
 *   ┌─────────────────────────────────────┐
 *   │ FACTOR                              │
 *   │ Nature of work                      │
 *   │                                     │
 *   │ RISK UP                             │
 *   │ Long paragraph...                   │
 *   │                                     │
 *   │ RISK DOWN                           │
 *   │ Long paragraph...                   │
 *   └─────────────────────────────────────┘
 */

function extractText(node: React.ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (!node) return "";
  if (isValidElement(node)) {
    return extractText((node.props as { children?: React.ReactNode }).children);
  }
  if (Array.isArray(node)) return node.map(extractText).join("");
  return "";
}

interface ParsedTable {
  headers: string[];
  rows: React.ReactNode[][];
}

function parseTableChildren(children: React.ReactNode): ParsedTable {
  const headers: string[] = [];
  const rows: React.ReactNode[][] = [];

  Children.forEach(children, (section) => {
    if (!isValidElement(section)) return;
    const sectionType = (section.type as string) || "";

    Children.forEach(
      (section.props as { children?: React.ReactNode }).children,
      (tr) => {
        if (!isValidElement(tr)) return;
        const cells: React.ReactNode[] = [];

        Children.forEach(
          (tr.props as { children?: React.ReactNode }).children,
          (cell) => {
            if (!isValidElement(cell)) return;
            const content = (cell.props as { children?: React.ReactNode })
              .children;
            cells.push(content);
          }
        );

        if (sectionType === "thead" || (section.type as any) === "thead") {
          cells.forEach((c) => headers.push(extractText(c)));
        } else {
          rows.push(cells);
        }
      }
    );
  });

  return { headers, rows };
}

export function TableCards({
  children,
}: {
  children: React.ReactNode;
}) {
  const { headers, rows } = parseTableChildren(children);

  // Fallback: if we can't parse, render nothing
  if (rows.length === 0 && headers.length === 0) return null;

  return (
    <div className="table-cards-container">
      {rows.map((row, rowIndex) => (
        <div key={rowIndex} className="analysis-card">
          {row.map((cell, cellIndex) => (
            <div key={cellIndex} className="analysis-card-field">
              {headers[cellIndex] && (
                <div className="analysis-card-label">
                  {headers[cellIndex]}
                </div>
              )}
              <div className="analysis-card-value">{cell}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
