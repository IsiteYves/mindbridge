import { useEffect, useState } from "react";
import { Link } from "react-router";

import { AssignmentList, Pager } from "@/components/AssignmentList";
import { type Assignment, apiRequest, errorMessage, type Page } from "@/lib/api";
import { stateLabel } from "@/lib/assignments";
import { toast } from "@/lib/toast";

const PAGE_SIZE = 15;

type StateFilter = "all" | "pending" | "closed";

export default function AssignmentSearchPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<StateFilter>("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [newestFirst, setNewestFirst] = useState(false);
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<Page<Assignment> | null>(null);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({
      q: query.trim(),
      state,
      sort: newestFirst ? "deadline_desc" : "deadline_asc",
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    const timer = window.setTimeout(() => {
      apiRequest<Page<Assignment>>(`/assignments?${params.toString()}`).then(
        (result) => {
          if (!cancelled) setPage(result);
        },
        (err: unknown) => toast.error(errorMessage(err)),
      );
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, state, from, to, newestFirst, offset]);

  function changeFilter<T>(setter: (value: T) => void, value: T) {
    setter(value);
    setOffset(0);
  }

  return (
    <section className="card">
      <div className="card-title">
        <h1>Search assignments</h1>
        <Link to="/assignments" className="button secondary compact">
          Back to my assignments
        </Link>
      </div>

      <div className="form-row">
        <label className="field">
          Name or course
          <input
            value={query}
            onChange={(event) => changeFilter(setQuery, event.target.value)}
            placeholder="e.g. Poster"
          />
        </label>
        <label className="field">
          Status
          <select value={state} onChange={(event) => changeFilter(setState, event.target.value as StateFilter)}>
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="closed">Closed or submitted</option>
          </select>
        </label>
      </div>

      <div className="form-row">
        <label className="field">
          Due from
          <input type="date" value={from} onChange={(event) => changeFilter(setFrom, event.target.value)} />
        </label>
        <label className="field">
          Due to
          <input type="date" value={to} onChange={(event) => changeFilter(setTo, event.target.value)} />
        </label>
        <label className="field">
          Order
          <select
            value={newestFirst ? "desc" : "asc"}
            onChange={(event) => changeFilter(setNewestFirst, event.target.value === "desc")}
          >
            <option value="asc">Earliest due first</option>
            <option value="desc">Latest due first</option>
          </select>
        </label>
      </div>

      <p className="muted small">
        {page === null ? "Loading…" : `${page.total} result${page.total === 1 ? "" : "s"}`}
      </p>

      {page && page.items.length === 0 && <p className="empty-state">No assignments match these filters.</p>}
      {page && page.items.length > 0 && (
        <>
          <AssignmentList items={page.items} badge={(a) => <span className="pill">{stateLabel(a)}</span>} />
          <Pager offset={page.offset} limit={page.limit} total={page.total} onChange={setOffset} />
        </>
      )}
    </section>
  );
}
