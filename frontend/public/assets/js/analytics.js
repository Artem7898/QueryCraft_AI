export function initAnalytics() {
  console.log('Analytics initialized');
}

export function trackSQLGeneration(complexity, success) {
  console.log(`Track: SQL ${complexity} - ${success ? 'success' : 'fail'}`);
}

export default { initAnalytics, trackSQLGeneration };