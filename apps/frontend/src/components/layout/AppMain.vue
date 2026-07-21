<template>
  <main class="app-main" data-main-content tabindex="-1">
    <slot />
  </main>
</template>

<style scoped>
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
