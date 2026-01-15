describe('QueryCraft AI E2E', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('should generate SQL query', () => {
    cy.get('[data-testid="table-input"]').type('users');
    cy.get('[data-testid="generate-btn"]').click();
    cy.get('[data-testid="sql-output"]').should('contain', 'SELECT');
  });
});