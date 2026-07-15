import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export interface ResearchTopic {
  name: string;
  description: string;
  createdAt: string; // ISO string
}

const STORAGE_KEY = 'hfb-current-research-topic';

function loadFromStorage(): ResearchTopic | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.name === 'string') {
      return parsed as ResearchTopic;
    }
    return null;
  } catch {
    return null;
  }
}

function saveToStorage(topic: ResearchTopic): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(topic));
}

function clearStorage(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export const useResearchStore = defineStore('research', () => {
  const currentTopic = ref<ResearchTopic | null>(loadFromStorage());

  const hasActiveResearch = computed(() => currentTopic.value !== null);

  function setTopic(name: string, description: string): ResearchTopic {
    const topic: ResearchTopic = {
      name,
      description: description || '',
      createdAt: new Date().toISOString(),
    };
    currentTopic.value = topic;
    saveToStorage(topic);
    return topic;
  }

  function clearTopic(): void {
    currentTopic.value = null;
    clearStorage();
  }

  return {
    currentTopic,
    hasActiveResearch,
    setTopic,
    clearTopic,
  };
});
