describe('QueryCraft AI E2E Tests', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('should generate SQL query from description', () => {
    cy.get('#queryInput').type('get all users');
    cy.get('#dbType').select('postgresql');
    cy.get('#generateBtn').click();

    cy.get('#queryOutput', { timeout: 10000 }).should('be.visible');
    cy.get('#queryOutput').should('contain', 'SELECT');
  });
});