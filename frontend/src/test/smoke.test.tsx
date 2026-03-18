/**
 * 烟雾测试: 验证 Vitest + jsdom + @testing-library/react 配置正确
 */
import { render, screen } from '@testing-library/react'

function HelloWorld() {
  return <div>Hello, Golden Flower!</div>
}

describe('Vitest Setup Smoke Test', () => {
  it('should have jsdom environment', () => {
    expect(typeof document).toBe('object')
    expect(typeof window).toBe('object')
  })

  it('should render a React component', () => {
    render(<HelloWorld />)
    expect(screen.getByText('Hello, Golden Flower!')).toBeInTheDocument()
  })
})
