<template>
  <main class="app-main">
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
