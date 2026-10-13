/** Build the existing learner routes from source-bound item and goal identities. */
export function practicePath(itemId: string, goalId?: string | null): string {
  return `/learn/practice/${encodeURIComponent(itemId)}${goalId ? `/goal/${encodeURIComponent(goalId)}` : ''}`;
}
