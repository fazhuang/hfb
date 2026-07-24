/**
 * useFocusTrap — Focus trap for dialogs, drawers, and dropdowns.
 *
 * When active, Tab/Shift+Tab cycles focus among focusable elements within
 * the container. On deactivate, focus is restored to the previously
 * focused element.
 *
 * Extracted from existing dialog implementations (CreateProjectDialog,
 * DeleteProjectDialog) into a shared composable.
 */
import { ref, onUnmounted } from 'vue';

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function useFocusTrap() {
  const containerRef = ref<HTMLElement | null>(null);
  let previousFocus: HTMLElement | null = null;

  function getFocusable(): HTMLElement[] {
    if (!containerRef.value) return [];
    return Array.from(containerRef.value.querySelectorAll(FOCUSABLE));
  }

  function activate(_triggerEl?: HTMLElement | null) {
    previousFocus = (document.activeElement as HTMLElement) || null;
    document.addEventListener('keydown', onKeyDown);
    // Trap focus to first focusable element
    const focusable = getFocusable();
    if (focusable.length > 0) {
      focusable[0]?.focus();
    } else {
      containerRef.value?.focus();
    }
  }

  function deactivate(triggerEl?: HTMLElement | null) {
    document.removeEventListener('keydown', onKeyDown);
    if (triggerEl && typeof triggerEl.focus === 'function') {
      triggerEl.focus();
    } else if (previousFocus && typeof previousFocus.focus === 'function') {
      previousFocus.focus();
    }
    previousFocus = null;
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key !== 'Tab') return;

    const focusable = getFocusable();
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }

    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;

    if (event.shiftKey) {
      if (document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  onUnmounted(() => {
    document.removeEventListener('keydown', onKeyDown);
  });

  return { containerRef, activate, deactivate };
}
