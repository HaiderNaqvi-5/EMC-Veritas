## 2024-05-19 - Missing useMemo in heavily interacted forms
**Learning:** Found multiple instances where large arrays were filtered or mapped during the render of forms containing controlled inputs. This triggers an O(N) re-calculation on every single keystroke.
**Action:** Always wrap heavy list operations (filtering, creating Maps/Sets) in `useMemo` when they depend on API data in a form component.
