---
id: behaviors/frontend/todo-list
version: "1.0.0"
status: approved
depends_on:
  - contracts/api/todos
  - contracts/ui/components
---

## Todo List Page Behavior

### Initial Load
- On mount, fetch all todos from GET /api/todos
- Display loading text `Loading...` while fetching
- On success, render TodoList with the returned todos
- On error, display "Failed to load todos. Try again." with a retry button
- The retry button may either refetch the todos in-place or trigger a full page reload that re-runs the fetch

### Adding a Todo
- User types in AddTodoForm and submits
- POST /api/todos with the title
- On success: prepend new todo to the list (no full refetch)
- On any non-2xx POST response, display inline error "Failed to add todo" below the form regardless of the specific API error payload

### Toggling Completion
- User clicks checkbox on a TodoItem
- PUT /api/todos/:id with `{ "completed": !current }` (optimistic update)
- On success: keep the toggled state
- On error: revert the toggle, display browser alert `Failed to update todo`

### Deleting a Todo
- User clicks delete button on a TodoItem
- Optimistically remove the todo from the list and immediately call DELETE /api/todos/:id
- On success: keep the todo removed
- On error: restore the deleted item and display browser alert `Failed to delete todo`

### Filtering
- TodoFilter at the top of the page
- "All" shows everything, "Active" shows `completed === false`, "Completed" shows `completed === true`
- Filter is client-side (no API call), applied to the already-fetched list
- Default filter on page load: "All"
