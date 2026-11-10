import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { exampleInput, exampleResolution, exampleTicket } from '../../test/deploy-examples.js'
import { ERROR_KINDS, STAGES } from './contract.js'

// 계약은 타입이라 tsc가 대부분을 검사한다(예시가 타입에 맞지 않으면 build가 깨진다). 여기서는 문서와 어긋나지 않는지만 본다.
describe('deploy contract', () => {
  it('matches the example in docs/design/deploy-handoff.md', () => {
    const doc = readFileSync(new URL('../../../docs/design/deploy-handoff.md', import.meta.url), 'utf8')
    const json = /```json\n([\s\S]*?)\n```/.exec(doc)?.[1]
    expect(json).toBeDefined()
    expect(JSON.parse(json!)).toEqual(exampleInput)
  })

  it('lists the pipeline stages in run order', () => {
    expect(STAGES).toEqual(['build', 'prepare', 'render', 'apply', 'verify', 'switch'])
  })

  it('keeps the shared error kinds', () => {
    expect(ERROR_KINDS).toContain(exampleTicket.errorKind)
    expect(ERROR_KINDS).toHaveLength(10)
  })
})

// 공유 계획 §4.3 예시가 타입에 맞는지 tsc로만 확인한다.
void exampleResolution
