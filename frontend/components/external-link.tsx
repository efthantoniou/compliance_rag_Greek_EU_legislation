import type { AnchorHTMLAttributes } from "react";

// react-markdown `a` renderer: EUR-Lex citation links should open in a new
// tab rather than navigating away from an in-progress answer.
export function ExternalLink(props: AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a
      {...props}
      target="_blank"
      rel="noopener noreferrer"
      className="underline underline-offset-2"
    />
  );
}
